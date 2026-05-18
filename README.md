# knct-hub

Smart context injection for AI coding agents. Per-project, hook-driven, observable.

## Logging spike

The current state is a minimal FastAPI server that logs every Claude Code hook event to a global SQLite database. No context is injected yet — the spike only observes.

### Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

### Run

```bash
python -m knct_hub
```

Server listens on `http://127.0.0.1:8765`.

### Database

Events are persisted to `~/.knct/hub.db` (auto-created on first request).

### Inspect traces

```bash
curl http://localhost:8765/traces        # last 100 events, JSON
curl 'http://localhost:8765/traces?limit=10'
sqlite3 ~/.knct/hub.db 'select ts, event, tool_name from traces order by ts desc limit 20'
```

### Wiring

This repo's `.claude/settings.json` already points Claude Code hooks at the local server for `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `Stop`. Start the server before opening the repo in Claude Code and traces will accumulate.
