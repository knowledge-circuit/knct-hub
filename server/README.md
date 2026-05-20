# knct-hub server

FastAPI hub server: ingests Claude Code hook events, resolves kpatches across org / project / member scopes, evaluates triggers, and returns injection payloads.

## Concepts

Every kpatch carries an explicit `scope` (`org`, `project`, or `member`).
For each hook the resolver collects rows at all three scopes for
`(caller_org, project, user)`, keeps the lowest-scope row per slug
(member > project > org), and drops any with `disable=true`. The
trigger engine then matches the survivors' triggers against the event
(`session_start`, `user_prompt`, `pre_tool_use`) and concatenates the
matching bodies into the `additionalContext` returned to the agent.

Override = create a sibling kpatch at a lower scope with new content.
Disable = create the sibling with `disable=true`. There are no separate
disable/override arrays.

## Layout

```
server/
├── pyproject.toml
├── alembic.ini
├── alembic/                  # migrations
│   ├── env.py
│   └── versions/
├── .env.example
└── src/knct_hub/
    ├── __main__.py           # uvicorn entry
    ├── app.py                # FastAPI factory + lifespan
    ├── config.py             # pydantic-settings
    ├── db/                   # SQLModel + async session
    ├── services/             # business logic per resource
    └── api/                  # routers (mounted under /api/v1)
```

## Run

```bash
uv sync
uv run python -m knct_hub
```

Server listens on `http://127.0.0.1:8765`. Every endpoint is under `/api/v1/`.

## Configuration

All settings are env-driven. Copy `.env.example` to `.env` and edit:

| Env var | Default | Notes |
|---------|---------|-------|
| `KNCT_DATABASE_URL` | `sqlite+aiosqlite:///~/.knct/hub.db` | SQLAlchemy URL. Use `postgresql+asyncpg://...` for Postgres. |
| `KNCT_HOST` | `127.0.0.1` | Bind address. Set `0.0.0.0` in containers. |
| `KNCT_PORT` | `8765` | |
| `KNCT_AUTO_MIGRATE` | `true` | Run `alembic upgrade head` on startup. Disable in deployments where ops handles migrations. |
| `KNCT_LOG_LEVEL` | `INFO` | |

## Migrations

```bash
# Apply pending migrations
uv run alembic upgrade head

# Create a new migration after editing src/knct_hub/db/models.py
uv run alembic revision --autogenerate -m "describe the change"

# Roll back one step
uv run alembic downgrade -1
```

On startup with `KNCT_AUTO_MIGRATE=true` (default), `upgrade head` runs automatically.

## Postgres

```bash
export KNCT_DATABASE_URL='postgresql+asyncpg://knct:knct@localhost:5432/knct'
uv run python -m knct_hub
```

The DB driver (`asyncpg`) is already declared in `pyproject.toml`.

## Inspect traces

```bash
curl 'http://localhost:8765/api/v1/traces?limit=20&only_injections=true'
sqlite3 ~/.knct/hub.db 'select ts, event, kpatch_ids from traces order by ts desc limit 20'
```
