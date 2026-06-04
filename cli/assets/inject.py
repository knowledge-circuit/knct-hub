#!/usr/bin/env python3
"""kpatch v0: UserPromptSubmit hook.

Reads kpatch markdown files, matches against the submitted prompt, prints
matched bodies to stdout for Claude Code to fold into context.
Fail-safe: any error -> silent, exit 0 (never block the prompt).
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    log: dict = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        data = json.loads(raw) if raw.strip() else {}
        prompt = str(data.get("prompt", "")).lower()
        session_id = data.get("session_id")
        log["session_id"] = session_id
        log["prompt_len"] = len(prompt)

        kpatch_dir = find_kpatch_dir()
        log["kpatch_dir"] = str(kpatch_dir) if kpatch_dir else None
        if not kpatch_dir:
            log["error"] = "no kpatch_dir found"
            return

        candidates = sorted(kpatch_dir.glob("*.md"))
        log["candidates"] = [p.stem for p in candidates]

        chunks = []
        names = []
        for path in candidates:
            meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            if not should_inject(meta, prompt):
                continue
            chunks.append(f"<!-- kpatch: {path.stem} -->\n{body.strip()}")
            names.append(path.stem)

        log["matched"] = names
        log["state_written"] = write_state(session_id, names)

        if chunks:
            sys.stdout.write("\n\n".join(chunks) + "\n")
    except Exception as e:
        log["error"] = f"{type(e).__name__}: {e}"
    finally:
        append_log(log)


def append_log(entry: dict) -> None:
    state_dir = state_dir_path()
    if not state_dir:
        return
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        with (state_dir / "inject.log").open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except OSError:
        return


def write_state(session_id, names) -> bool:
    if not session_id:
        return False
    state_dir = state_dir_path()
    if not state_dir:
        return False
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / f"{session_id}.json").write_text(
            json.dumps({"kpatches": names}), encoding="utf-8"
        )
        return True
    except OSError:
        return False


def state_dir_path() -> Path | None:
    proj = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not proj:
        return None
    return Path(proj) / ".knct" / "state"


def find_kpatch_dir() -> Path | None:
    candidates = []
    proj = os.environ.get("CLAUDE_PROJECT_DIR")
    if proj:
        candidates.append(Path(proj) / ".knct" / "kpatches")
    candidates.append(Path.cwd() / ".knct" / "kpatches")
    candidates.append(Path.home() / ".knct" / "kpatches")
    for c in candidates:
        try:
            if c.is_dir():
                return c
        except OSError:
            continue
    return None


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)
KV_RE = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$")


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    meta: dict = {}
    for line in m.group(1).splitlines():
        kv = KV_RE.match(line)
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2).strip()
        if val == "true":
            meta[key] = True
        elif val == "false":
            meta[key] = False
        elif val.startswith("[") and val.endswith("]"):
            items = [s.strip().strip("'\"") for s in val[1:-1].split(",")]
            meta[key] = [s for s in items if s]
        else:
            meta[key] = val.strip("'\"")
    return meta, m.group(2)


def should_inject(meta: dict, prompt_lower: str) -> bool:
    if meta.get("always") is True:
        return True
    triggers = meta.get("triggers")
    if not isinstance(triggers, list):
        return False
    return any(t and str(t).lower() in prompt_lower for t in triggers)


if __name__ == "__main__":
    main()
