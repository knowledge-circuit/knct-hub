## Why

We need to validate the core thesis of knct-hub — that hook-driven context injection into Claude Code is viable — before designing the rules engine, skills model, or any production-shaped server. The cheapest way to de-risk this is to stand up the dumbest possible hub that just receives every hook event and logs the raw payload to disk. Real wire-format traffic answers questions that documentation does not: payload shapes, event frequency, latency budget, session correlation across resume and compaction.

## What Changes

- Add a minimal FastAPI server (`knct-hub`) that accepts POSTs from Claude Code HTTP hooks and writes every received event to a single SQLite database.
- Add a `GET /traces` JSON endpoint to inspect captured events.
- Use a global on-disk database at `~/.knct/hub.db` (created on first request).
- Configure this repo's `.claude/settings.json` to point Claude Code hooks at the local server on port 8765 for `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `Stop`.
- All hook responses return an empty JSON object — no context is injected; the spike only observes.

## Capabilities

### New Capabilities
- `hook-logging`: receive Claude Code hook events over HTTP, persist their raw payloads to SQLite, and expose them for inspection.

### Modified Capabilities
<!-- none — no prior specs exist -->

## Impact

- New Python project (FastAPI + uvicorn + stdlib sqlite3) at the repo root.
- New `~/.knct/hub.db` SQLite file on the developer machine (auto-created).
- New `.claude/settings.json` in this repo wiring hooks to `http://localhost:8765/hook`.
- No production systems, no external services, no auth. Local-only spike.
- Output of this spike directly informs the design of the follow-on `add-injection-engine` change.
