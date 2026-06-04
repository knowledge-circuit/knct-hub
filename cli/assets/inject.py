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
from pathlib import Path


def main() -> None:
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        data = json.loads(raw) if raw.strip() else {}
        prompt = str(data.get("prompt", "")).lower()

        kpatch_dir = find_kpatch_dir()
        if not kpatch_dir:
            return

        chunks = []
        names = []
        for path in sorted(kpatch_dir.glob("*.md")):
            meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            if not should_inject(meta, prompt):
                continue
            chunks.append(f"<!-- kpatch: {path.stem} -->\n{body.strip()}")
            names.append(path.stem)

        write_state(data.get("session_id"), names)

        if chunks:
            sys.stdout.write("\n\n".join(chunks) + "\n")
    except Exception:
        # fail-safe: swallow, exit 0
        return


def write_state(session_id, names) -> None:
    if not session_id:
        return
    proj = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    state_dir = Path(proj) / ".knct" / "state"
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / f"{session_id}.json").write_text(
            json.dumps({"kpatches": names}), encoding="utf-8"
        )
    except OSError:
        return


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
