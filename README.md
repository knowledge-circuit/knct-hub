# knct-hub

Smart context injection for AI coding agents. Per-project, hook-driven, observable.

## Monorepo layout

```
knct-hub/
├── server/    # FastAPI hub server (Python).  Run locally or deploy.
├── cli/       # @knct/cli — npx-installable CLI (TypeScript).
├── .knct/     # this repo's own knct config (we dogfood)
└── .claude/   # this repo's own Claude Code hook wiring
```

See [`server/`](./server) and [`cli/`](./cli) for component-level docs.

## Quick start

Run the hub locally:

```bash
cd server
uv run python -m knct_hub          # listens on http://127.0.0.1:8765
```

All endpoints live under `/api/v1/...`. Database lives at `~/.knct/hub.db` (SQLite by default; Postgres supported via `KNCT_DATABASE_URL`).

In any repo you want to wire up:

```bash
npx @knct/cli init
```

This writes `.knct/config.toml` and `.claude/settings.json`. Restart Claude Code to pick up the hooks.

## Inspect traces

```bash
curl 'http://localhost:8765/api/v1/traces?limit=10'
sqlite3 ~/.knct/hub.db 'select ts, event, tool_name from traces order by ts desc limit 20'
```

## Status

Early. The injection engine works end-to-end (skills, rules, dedupe). The CLI handles initial wiring. There is no auth, no UI, and no published npm package yet.
