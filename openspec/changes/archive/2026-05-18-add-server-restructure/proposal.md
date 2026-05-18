## Why

The server is currently one 300-line file with raw SQL, schema-on-startup, and zero versioning on its HTTP surface. That's the right shape for a spike, the wrong shape for what's coming next: a UI, authentication, audit logs, Postgres in production, and ongoing schema evolution. Restructuring while there's barely any code costs almost nothing; postponing it until after the UI lands is meaningfully painful. This change replaces the single file with a properly split module tree, introduces SQLModel + Alembic so schema changes become tracked migrations, adds Pydantic-driven settings, supports both SQLite and Postgres via `DATABASE_URL`, and versions every endpoint under `/api/v1/`.

## What Changes

- **BREAKING (API)**: every existing endpoint moves under `/api/v1/`. `POST /hook` → `POST /api/v1/hook`, `GET /traces` → `GET /api/v1/traces`, `GET/POST /projects` and nested skill/rule routes get the same prefix. There is no compatibility shim — all clients must update.
- Split `src/knct_hub/server.py` into a proper module tree: `app.py`, `config.py`, `db/`, `services/`, `api/` (one file per resource).
- Adopt **SQLModel** for all tables, replacing raw SQL and stringly-typed columns. SQLModel classes become both the ORM models and the API schemas where shapes align; dedicated Pydantic schemas live in `schemas/` where they diverge.
- Add **Alembic** migrations. Wipe the existing `~/.knct/hub.db`, autogenerate one baseline migration from the SQLModel metadata, and run `alembic upgrade head` on startup (controlled by `KNCT_AUTO_MIGRATE`, default `true`).
- Add **pydantic-settings** for config. `Settings` reads `DATABASE_URL`, `KNCT_HOST`, `KNCT_PORT`, `KNCT_AUTO_MIGRATE`, `KNCT_LOG_LEVEL` from environment / `.env`.
- Support both **SQLite** (default: `sqlite+aiosqlite:///~/.knct/hub.db`) and **Postgres** (`postgresql+asyncpg://...`) via the URL. Async engine throughout.
- Update the `@knct/cli` package to write the `/api/v1/hook` URL into `.claude/settings.json` and to use `/api/v1/projects` for the picker.
- Update this repo's `.claude/settings.json` to point at `/api/v1/hook`.

## Capabilities

### New Capabilities
- `server-config`: Pydantic-driven settings (env / `.env`), DATABASE_URL switching between SQLite and Postgres, and Alembic-managed schema migrations.
- `api-versioning`: every HTTP endpoint is served under the `/api/v1/` prefix; future major versions can coexist under additional prefixes.

### Modified Capabilities
- `hook-logging`: ingestion and trace endpoints move under `/api/v1/`.
- `project-registry`: list and create endpoints move under `/api/v1/`; slug header remains.
- `skill-store`: CRUD endpoints move under `/api/v1/`.
- `rule-engine`: CRUD endpoints move under `/api/v1/`.
- `cli-init`: hub URL resolution unchanged, but the URL the CLI hits and the URL it writes into `.claude/settings.json` are now `/api/v1/...`.

## Impact

- Server requires Python ≥ 3.10 (already true), plus new dependencies: `sqlmodel`, `alembic`, `aiosqlite`, `asyncpg`, `pydantic-settings`.
- Existing local databases at `~/.knct/hub.db` will be wiped as part of the migration baseline. Pre-existing traces and projects are lost.
- All HTTP clients break until they switch to `/api/v1/...`. Only known client is `@knct/cli` (updated here) and this repo's `.claude/settings.json` (updated here).
- Docker/PyPI distribution is out of scope; this change preserves the current `python -m knct_hub` entry point.
- No UI, no authentication, no observability dashboards — those are deliberately deferred to follow-on changes.
- Database engine swap to Postgres is *supported* but not exercised in CI or default; SQLite remains the default for local use.
