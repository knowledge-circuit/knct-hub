import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request


def db_path() -> Path:
    p = Path.home() / ".knct" / "hub.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY,
                ts TEXT NOT NULL,
                event TEXT NOT NULL,
                session_id TEXT,
                cwd TEXT,
                tool_name TEXT,
                payload TEXT NOT NULL
            )
            """
        )


def insert_trace(payload: dict) -> None:
    event = payload.get("hook_event_name") or "<unknown>"
    session_id = payload.get("session_id")
    cwd = payload.get("cwd")
    tool_input = payload.get("tool_input") or {}
    tool_name = payload.get("tool_name") or tool_input.get("tool_name")
    ts = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute(
            "INSERT INTO traces (ts, event, session_id, cwd, tool_name, payload) VALUES (?, ?, ?, ?, ?, ?)",
            (ts, event, session_id, cwd, tool_name, json.dumps(payload)),
        )


app = FastAPI()


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.post("/hook")
async def hook(request: Request) -> dict:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid JSON")
    if not isinstance(payload, dict):
        payload = {"_raw": payload}
    insert_trace(payload)
    return {}


@app.get("/traces")
def traces(limit: int = 100) -> list[dict]:
    limit = max(1, min(limit, 1000))
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, ts, event, session_id, cwd, tool_name, payload FROM traces ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["payload"] = json.loads(d["payload"])
        except (TypeError, json.JSONDecodeError):
            pass
        out.append(d)
    return out
