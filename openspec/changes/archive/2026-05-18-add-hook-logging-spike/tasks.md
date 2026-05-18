## 1. Project scaffold

- [x] 1.1 Create `pyproject.toml` declaring a `knct-hub` package with deps `fastapi`, `uvicorn[standard]`
- [x] 1.2 Create `src/knct_hub/__init__.py` and `src/knct_hub/server.py`
- [x] 1.3 Add `.gitignore` entries for `__pycache__/`, `.venv/`, `*.egg-info/`

## 2. Storage layer

- [x] 2.1 In `server.py`, define DB path resolver returning `~/.knct/hub.db`, creating the directory if missing
- [x] 2.2 Implement `init_db()` that opens the SQLite connection and runs `CREATE TABLE IF NOT EXISTS traces (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, event TEXT NOT NULL, session_id TEXT, cwd TEXT, tool_name TEXT, payload TEXT NOT NULL)`
- [x] 2.3 Implement `insert_trace(payload: dict)` extracting `hook_event_name`, `session_id`, `cwd`, `tool_input.tool_name` (best-effort) and storing the full payload as JSON text with ISO-8601 timestamp

## 3. HTTP endpoints

- [x] 3.1 Implement `POST /hook` that parses JSON body, calls `insert_trace`, returns `{}`
- [x] 3.2 Reject non-JSON bodies with FastAPI's default 422 (no custom handling needed)
- [x] 3.3 Implement `GET /traces?limit=N` (default 100) returning rows ordered by `ts DESC` as JSON array, with `payload` parsed back to an object

## 4. Run + smoke

- [x] 4.1 Add a `python -m knct_hub` entrypoint that runs `uvicorn` on `127.0.0.1:8765`
- [ ] 4.2 Manually verify: start the server, `curl -X POST localhost:8765/hook -d '{"hook_event_name":"Test"}' -H 'content-type: application/json'`, then `curl localhost:8765/traces` shows the row

## 5. Wire into this repo

- [x] 5.1 Create `.claude/settings.json` with `hooks` entries for `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, each using `{ "type": "http", "url": "http://localhost:8765/hook" }`
- [ ] 5.2 Start the server, open this repo in Claude Code, run a trivial prompt
- [ ] 5.3 Confirm `GET /traces` shows rows for at least `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`

## 6. Document

- [x] 6.1 Add a short `README.md` section explaining: install, run, where the DB lives, how to inspect traces
