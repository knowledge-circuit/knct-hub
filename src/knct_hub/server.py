import json
import sqlite3
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel


# ---------- storage ----------


def db_path() -> Path:
    p = Path.home() / ".knct" / "hub.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    event TEXT NOT NULL,
    session_id TEXT,
    cwd TEXT,
    tool_name TEXT,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
    slug TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS skills (
    id TEXT NOT NULL,
    project_slug TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    body TEXT NOT NULL,
    keywords TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (project_slug, id)
);
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_slug TEXT NOT NULL,
    on_event TEXT NOT NULL,
    match TEXT,
    inject TEXT NOT NULL,
    once_per_session INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS rules_lookup ON rules(project_slug, on_event);
CREATE TABLE IF NOT EXISTS session_dedupe (
    session_id TEXT NOT NULL,
    rule_id INTEGER NOT NULL,
    fired_at TEXT NOT NULL,
    PRIMARY KEY (session_id, rule_id)
);
"""


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(traces)")}
        if "response" not in cols:
            conn.execute("ALTER TABLE traces ADD COLUMN response TEXT")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        conn.execute("DELETE FROM session_dedupe WHERE fired_at < ?", (cutoff,))


def insert_trace(payload: dict, response: dict) -> None:
    event = payload.get("hook_event_name") or "<unknown>"
    session_id = payload.get("session_id")
    cwd = payload.get("cwd")
    tool_input = payload.get("tool_input") or {}
    tool_name = payload.get("tool_name") or tool_input.get("tool_name")
    ts = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute(
            "INSERT INTO traces (ts, event, session_id, cwd, tool_name, payload, response)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, event, session_id, cwd, tool_name, json.dumps(payload), json.dumps(response)),
        )


def ensure_project(slug: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO projects (slug, created_at) VALUES (?, ?)",
            (slug, datetime.now(timezone.utc).isoformat()),
        )


# ---------- engine ----------


def _target_path(payload: dict) -> str:
    ti = payload.get("tool_input") or {}
    return ti.get("file_path") or payload.get("cwd") or ""


def evaluate(slug: str, on_event: str, payload: dict) -> list[str]:
    """Return ordered list of skill ids to inject. Records dedupe fires."""
    session_id = payload.get("session_id") or ""
    target = _target_path(payload)
    with connect() as conn:
        rules = conn.execute(
            "SELECT id, match, inject, once_per_session FROM rules"
            " WHERE project_slug=? AND on_event=? ORDER BY id",
            (slug, on_event),
        ).fetchall()
        if not rules:
            return []
        fired = {
            r["rule_id"]
            for r in conn.execute(
                "SELECT rule_id FROM session_dedupe WHERE session_id=?", (session_id,)
            ).fetchall()
        }
        selected: list[str] = []
        to_record: list[int] = []
        for r in rules:
            if r["match"] and not fnmatch(target, r["match"]):
                continue
            if r["once_per_session"] and r["id"] in fired:
                continue
            selected.extend(json.loads(r["inject"]))
            if r["once_per_session"]:
                to_record.append(r["id"])
        if to_record and session_id:
            now = datetime.now(timezone.utc).isoformat()
            conn.executemany(
                "INSERT OR IGNORE INTO session_dedupe (session_id, rule_id, fired_at)"
                " VALUES (?, ?, ?)",
                [(session_id, rid, now) for rid in to_record],
            )
    return selected


def fetch_skills(slug: str, ids: list[str]) -> list[dict]:
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    with connect() as conn:
        rows = conn.execute(
            f"SELECT id, name, description, body, keywords FROM skills"
            f" WHERE project_slug=? AND id IN ({placeholders})",
            (slug, *ids),
        ).fetchall()
    by_id = {r["id"]: dict(r) for r in rows}
    return [by_id[i] for i in ids if i in by_id]


def concat_bodies(skills: list[dict]) -> str:
    return "\n\n---\n\n".join(s["body"] for s in skills)


def inject_response(event_name: str, markdown: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": markdown,
        }
    }


# ---------- per-event handlers ----------


def handle_session_start(slug: str, payload: dict) -> dict:
    with connect() as conn:
        skills = conn.execute(
            "SELECT id, name, description FROM skills WHERE project_slug=? ORDER BY id",
            (slug,),
        ).fetchall()
        (rule_count,) = conn.execute(
            "SELECT COUNT(*) FROM rules WHERE project_slug=?", (slug,)
        ).fetchone()
    if not skills and not rule_count:
        return {}
    lines = [f"This project has {len(skills)} skills and {rule_count} rules."]
    if skills:
        lines.append("")
        for s in skills:
            desc = s["description"] or ""
            lines.append(f"- **{s['name']}** (`{s['id']}`): {desc}")
    return inject_response("SessionStart", "\n".join(lines))


def handle_prompt_submit(slug: str, payload: dict) -> dict:
    prompt = (payload.get("prompt") or "").lower()
    if not prompt:
        return {}
    with connect() as conn:
        skills = conn.execute(
            "SELECT id, body, keywords FROM skills WHERE project_slug=?", (slug,)
        ).fetchall()
    matched = []
    for s in skills:
        kws = json.loads(s["keywords"] or "[]")
        if any(k and k.lower() in prompt for k in kws):
            matched.append(dict(s))
    if not matched:
        return {}
    return inject_response("UserPromptSubmit", concat_bodies(matched))


def handle_pre_tool(slug: str, payload: dict) -> dict:
    tool = payload.get("tool_name") or (payload.get("tool_input") or {}).get("tool_name")
    if tool in ("Edit", "Write"):
        on = "pre_edit"
    elif tool == "Read":
        on = "pre_read"
    else:
        return {}
    ids = evaluate(slug, on, payload)
    if not ids:
        return {}
    skills = fetch_skills(slug, ids)
    if not skills:
        return {}
    return inject_response("PreToolUse", concat_bodies(skills))


def handle_post_compact(slug: str, payload: dict) -> dict:
    sid = payload.get("session_id")
    if sid:
        with connect() as conn:
            conn.execute("DELETE FROM session_dedupe WHERE session_id=?", (sid,))
    return {}


# ---------- HTTP app ----------


app = FastAPI()


@app.on_event("startup")
def _startup() -> None:
    init_db()


def _slug_from(request: Request) -> str:
    slug = request.headers.get("x-project-slug")
    if not slug:
        raise HTTPException(status_code=400, detail="missing X-Project-Slug header")
    return slug


@app.post("/hook")
async def hook(request: Request) -> dict:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid JSON")
    if not isinstance(payload, dict):
        payload = {"_raw": payload}
    slug = _slug_from(request)
    ensure_project(slug)
    event = payload.get("hook_event_name")
    if event == "SessionStart":
        resp = handle_session_start(slug, payload)
    elif event == "UserPromptSubmit":
        resp = handle_prompt_submit(slug, payload)
    elif event == "PreToolUse":
        resp = handle_pre_tool(slug, payload)
    elif event == "PostCompact":
        resp = handle_post_compact(slug, payload)
    else:
        resp = {}
    insert_trace(payload, resp)
    return resp


@app.get("/traces")
def traces(limit: int = 100) -> list[dict]:
    limit = max(1, min(limit, 1000))
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, ts, event, session_id, cwd, tool_name, payload, response"
            " FROM traces ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        for k in ("payload", "response"):
            v = d.get(k)
            if v:
                try:
                    d[k] = json.loads(v)
                except (TypeError, json.JSONDecodeError):
                    pass
        out.append(d)
    return out


# ---------- CRUD: skills ----------


class SkillBody(BaseModel):
    name: str
    description: str | None = None
    body: str
    keywords: list[str] = []


@app.get("/projects/{slug}/skills")
def list_skills(slug: str) -> list[dict]:
    ensure_project(slug)
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, name, description, body, keywords FROM skills"
            " WHERE project_slug=? ORDER BY id",
            (slug,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["keywords"] = json.loads(d["keywords"] or "[]")
        out.append(d)
    return out


@app.get("/projects/{slug}/skills/{skill_id}")
def get_skill(slug: str, skill_id: str) -> dict:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, name, description, body, keywords FROM skills"
            " WHERE project_slug=? AND id=?",
            (slug, skill_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="skill not found")
    d = dict(row)
    d["keywords"] = json.loads(d["keywords"] or "[]")
    return d


@app.put("/projects/{slug}/skills/{skill_id}")
def put_skill(slug: str, skill_id: str, body: SkillBody) -> dict:
    ensure_project(slug)
    with connect() as conn:
        conn.execute(
            "INSERT INTO skills (id, project_slug, name, description, body, keywords)"
            " VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(project_slug, id) DO UPDATE SET"
            "   name=excluded.name, description=excluded.description,"
            "   body=excluded.body, keywords=excluded.keywords",
            (skill_id, slug, body.name, body.description, body.body, json.dumps(body.keywords)),
        )
    return {"ok": True, "id": skill_id}


@app.delete("/projects/{slug}/skills/{skill_id}")
def delete_skill(slug: str, skill_id: str) -> dict:
    with connect() as conn:
        cur = conn.execute(
            "DELETE FROM skills WHERE project_slug=? AND id=?", (slug, skill_id)
        )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="skill not found")
    return {"ok": True}


# ---------- CRUD: rules ----------


class RuleBody(BaseModel):
    on_event: str
    match: str | None = None
    inject: list[str]
    once_per_session: bool | None = None


def _normalize_once(body: RuleBody) -> int:
    if body.once_per_session is not None:
        return int(body.once_per_session)
    return 1 if body.on_event == "pre_read" else 0


@app.get("/projects/{slug}/rules")
def list_rules(slug: str) -> list[dict]:
    ensure_project(slug)
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, on_event, match, inject, once_per_session FROM rules"
            " WHERE project_slug=? ORDER BY id",
            (slug,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["inject"] = json.loads(d["inject"])
        d["once_per_session"] = bool(d["once_per_session"])
        out.append(d)
    return out


@app.post("/projects/{slug}/rules")
def create_rule(slug: str, body: RuleBody) -> dict:
    ensure_project(slug)
    once = _normalize_once(body)
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO rules (project_slug, on_event, match, inject, once_per_session)"
            " VALUES (?, ?, ?, ?, ?)",
            (slug, body.on_event, body.match, json.dumps(body.inject), once),
        )
    return {"id": cur.lastrowid}


@app.put("/projects/{slug}/rules/{rule_id}")
def update_rule(slug: str, rule_id: int, body: RuleBody) -> dict:
    once = _normalize_once(body)
    with connect() as conn:
        cur = conn.execute(
            "UPDATE rules SET on_event=?, match=?, inject=?, once_per_session=?"
            " WHERE project_slug=? AND id=?",
            (body.on_event, body.match, json.dumps(body.inject), once, slug, rule_id),
        )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="rule not found")
    return {"ok": True}


@app.delete("/projects/{slug}/rules/{rule_id}")
def delete_rule(slug: str, rule_id: int) -> dict:
    with connect() as conn:
        cur = conn.execute(
            "DELETE FROM rules WHERE project_slug=? AND id=?", (slug, rule_id)
        )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="rule not found")
    return {"ok": True}
