## Context

After three landed changes the server holds the engine, project/skill/rule CRUD, and hook ingestion — all in one Python file with raw `sqlite3`, schema-on-startup, hand-written JSON serialization, and no settings layer. The product roadmap (UI, auth, Postgres deployment, audit history) cannot land cleanly on top of that. This change is the foundational refactor that prepares the codebase to grow without becoming a tar pit.

It explicitly does *not* add features — it preserves behavior while turning the codebase into something that can absorb the next year of changes.

## Goals / Non-Goals

**Goals:**
- One file per resource in `api/`, one service per resource in `services/`, one place for DB session management, one place for settings.
- SQLModel classes as the single source of truth for table shape and (where shapes match) API I/O.
- Migrations as files in `alembic/versions/`, generated from SQLModel metadata.
- Postgres support behind a `DATABASE_URL`. SQLite remains the default for local use.
- Every endpoint versioned under `/api/v1/`. Adding `/api/v2/` later is a routing change, not a structural one.
- The CLI and this repo's `.claude/settings.json` updated to track the new paths so the system continues to work end-to-end after the change lands.

**Non-Goals:**
- Adding any new endpoint or behavior.
- Auth, rate limiting, CORS hardening — separate changes.
- UI integration — separate change (`add-web-ui` planned).
- Docker / PyPI publishing — separate change (`add-server-distribution`).
- Test suite — explicitly skipped per user direction; behavior is verified by manual smoke tests after the restructure.
- Data migration. The existing `~/.knct/hub.db` holds only smoke-test rows; we wipe and let Alembic regenerate.
- Pluggable storage backends beyond what SQLAlchemy already abstracts.

## Decisions

**SQLModel for ORM + schemas.** SQLModel unifies SQLAlchemy tables and Pydantic models in one class hierarchy. Considered: SQLAlchemy + separate Pydantic schemas (more boilerplate, more duplication of field definitions) — rejected. Considered: stay on raw `sqlite3` (less magic, less leverage as schema grows) — rejected, doesn't generalize to Postgres or migrations.

**Async engine throughout.** `aiosqlite` for SQLite, `asyncpg` for Postgres. FastAPI is async-first; using sync sessions inside async endpoints requires `run_in_executor` hacks. Considered: sync engine (simpler today, harder later) — rejected; the cost of going async now is one helper module.

**Alembic with autogenerate baseline.** On a clean repo with no existing prod databases, the simplest path is to wipe `~/.knct/hub.db`, run `alembic init`, point env.py at SQLModel metadata, and `alembic revision --autogenerate -m "baseline"`. The resulting migration is the canonical schema. Considered: hand-written first migration matching today's schema — rejected, more error-prone for no benefit.

**Auto-migrate on startup, opt-out via env.** `KNCT_AUTO_MIGRATE=true` (default) runs `alembic upgrade head` during the FastAPI lifespan. For solo / local use this is the right UX — install and run. For deployed environments where ops controls migration timing, set `KNCT_AUTO_MIGRATE=false` and run `alembic upgrade head` from the deploy pipeline. Considered: always require explicit migration — rejected, hurts local DX. Considered: never auto-migrate — same.

**`/api/v1/` prefix on every endpoint.** Including `/hook`. Yes, that means Claude Code's hook URL becomes `/api/v1/hook` — slightly uglier, but consistency across the API surface is worth more than a clean single-route exception. Versioning policy: `/api/v2/` happens when we make a breaking change we can't absorb without one. Considered: only versioning resource endpoints, leaving `/hook` at root — rejected, the inconsistency would bite later. Considered: no versioning yet — rejected, the change is cheaper now than after a published UI talks to it.

**One router per file, mounted in `app.py`.** Each `api/<resource>.py` exports an `APIRouter`. `app.py` includes them all with the `/api/v1` prefix. This makes adding `v2` later a single line per resource. Considered: APIRouter with `prefix="/v1"` per file — rejected, leaks the version into every file; the prefix is composition-level.

**Pydantic-settings for config.** Standard, well-supported, replaces ad-hoc constants. Settings class is a singleton imported where needed. `.env` parsing built in. Considered: `python-dotenv` + manual reads — rejected, no type safety. Considered: dynaconf, hydra — rejected, overkill.

**SQLite default URL: `sqlite+aiosqlite:///<home>/.knct/hub.db`.** Resolved at Settings init via expanduser. The home-dir default is preserved from current behavior so local users see no change.

**Database engine swap is a configuration choice, not a code branch.** SQLAlchemy abstracts dialect; our SQL stays standard. No `if postgres:` anywhere. The only Postgres-specific bit is the URL and dependency installation.

**CLI updates ship inside this change.** The restructure breaks the CLI; shipping them together avoids a half-broken state on `main`. The CLI changes are small (two URL constants and one path concatenation), so coupling them to this change is the right tradeoff.

**No tests.** Explicit user call. Behavior verification is manual smoke (existing test scripts re-run after the refactor). Adding a real test suite is a deliberate later milestone.

## Risks / Trade-offs

- **Async sessions are more verbose than sync** → mitigated by a clean `get_session` dependency. New contributors face mildly more ceremony but standard FastAPI idiom.
- **SQLModel is younger than SQLAlchemy** → relies on SQLAlchemy under the hood; SQLModel is just a thinner facade. Risk is bounded.
- **Wipe destroys local trace history** → accepted; rows are spike data and there's no value in them.
- **Auto-migrate on startup may fail loudly in unexpected ways (locked DB, etc.)** → mitigated by clear startup logging; if it becomes a problem, ship a `knct migrate` subcommand later.
- **`/api/v1/hook` is slightly ugly for hook config** → accepted as consistency tax; the CLI hides it from users entirely.
- **No tests means refactor regressions are caught only by smoke** → accepted with eyes open; explicitly an open follow-up.

## Migration Plan

1. Wipe `~/.knct/hub.db` once at the start of implementation.
2. After alembic baseline is generated, `alembic upgrade head` re-creates the schema.
3. Update this repo's `.claude/settings.json` to point at `/api/v1/hook` so the live session continues working post-restructure.
4. Update CLI in the same change; rebuild and (optionally) `npm link` to pick up the new URLs.
5. After landing, advise any other dev who happened to clone this repo to delete their `~/.knct/hub.db` and restart.

## Open Questions

- **Async migrations with Alembic.** Alembic itself is sync. Standard pattern: run sync engine inside `env.py` even when the app uses async. No real issue; flagging because it surprises people.
- **Where do app-level secrets eventually live?** Out of scope now; punt to the auth change.
- **Logging strategy.** Stdlib `logging` plus uvicorn's defaults for now. Revisit when ops concerns arrive.
