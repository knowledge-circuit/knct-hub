## 1. Dependencies and scaffold

- [x] 1.1 Update `server/pyproject.toml` to add `sqlmodel`, `alembic`, `aiosqlite`, `asyncpg`, `pydantic-settings`
- [x] 1.2 `uv sync` and confirm clean install
- [x] 1.3 Wipe `~/.knct/hub.db` (`rm -f` — accept loss of spike data)

## 2. Settings layer

- [x] 2.1 Create `src/knct_hub/config.py` with a `Settings(BaseSettings)` class exposing `database_url`, `host`, `port`, `auto_migrate`, `log_level`
- [x] 2.2 Provide `get_settings()` (lru_cache'd) returning a singleton
- [x] 2.3 Default `database_url` to `sqlite+aiosqlite:///<expanduser ~/.knct/hub.db>`
- [x] 2.4 Configure `.env` reading; add `.env.example` documenting all keys

## 3. DB layer

- [x] 3.1 Create `src/knct_hub/db/session.py` with `create_async_engine(...)` and an `async def get_session()` FastAPI dependency
- [x] 3.2 Create `src/knct_hub/db/models.py` defining SQLModel classes: `Trace`, `Project`, `Skill`, `Rule`, `SessionDedupe` — matching existing schema field-for-field
- [x] 3.3 Ensure each model includes appropriate indexes (rules: `(project_slug, on_event)`; session_dedupe: composite PK)
- [x] 3.4 Choose Pydantic configuration that lets SQLModel classes serialize JSON list/array columns correctly (or use plain TEXT + property accessors)

## 4. Alembic

- [x] 4.1 `cd server && uv run alembic init alembic`
- [x] 4.2 Edit `alembic/env.py` to import `Settings` and use the same `database_url`; set `target_metadata = SQLModel.metadata`; switch to async-friendly migration runner per Alembic's async cookbook
- [x] 4.3 Run `alembic revision --autogenerate -m "baseline"`; review and trim the generated migration
- [x] 4.4 `alembic upgrade head` against a clean DB; confirm tables match expectations

## 5. Services

- [x] 5.1 Create `src/knct_hub/services/projects.py` — `ensure_project`, `list_projects`, `create_project`
- [x] 5.2 Create `src/knct_hub/services/skills.py` — list/get/upsert/delete
- [x] 5.3 Create `src/knct_hub/services/rules.py` — list/create/update/delete
- [x] 5.4 Create `src/knct_hub/services/engine.py` — `evaluate(slug, on_event, payload)` with dedupe semantics
- [x] 5.5 Create `src/knct_hub/services/injection.py` — `inject_response`, `handle_session_start`, `handle_prompt_submit`, `handle_pre_tool`, `handle_post_compact`

## 6. API routers

- [x] 6.1 Create `src/knct_hub/api/hooks.py` with the `/hook` and `/traces` routes (no version prefix in the file itself)
- [x] 6.2 Create `src/knct_hub/api/projects.py` with `/projects` list + create
- [x] 6.3 Create `src/knct_hub/api/skills.py` with `/projects/{slug}/skills...` CRUD
- [x] 6.4 Create `src/knct_hub/api/rules.py` with `/projects/{slug}/rules...` CRUD

## 7. App composition

- [x] 7.1 Create `src/knct_hub/app.py` exporting a `create_app()` factory that composes the routers with `prefix="/api/v1"`
- [x] 7.2 Implement a FastAPI lifespan that, when `auto_migrate=True`, runs `alembic upgrade head` programmatically before accepting traffic
- [x] 7.3 Update `src/knct_hub/__main__.py` to call `uvicorn.run(create_app(), host=settings.host, port=settings.port)`
- [x] 7.4 Delete the old `src/knct_hub/server.py` once the new modules cover its surface

## 8. CLI updates

- [x] 8.1 In `cli/src/cli.ts`, update `fetchProjects` to GET `${hubUrl}/api/v1/projects`
- [x] 8.2 Update `createProject` to POST `${hubUrl}/api/v1/projects`
- [x] 8.3 Update `writeClaudeSettings` so each hook entry's URL ends with `/api/v1/hook`
- [x] 8.4 `npm run build` and verify the new bundle still functions end-to-end against the restructured server

## 9. Repo wiring

- [x] 9.1 Update this repo's `.claude/settings.json` so all six hook entries point at `http://localhost:8765/api/v1/hook`

## 10. Smoke

- [x] 10.1 Start the server; confirm `GET /api/v1/projects` returns `[]` against a freshly migrated DB
- [x] 10.2 Re-run the engine smoke script (CRUD + four-event injection + dedupe + PostCompact) against the new paths
- [x] 10.3 Run `knct init` against the server in a scratch directory; confirm it creates files with the new `/api/v1/hook` URL

## 11. Docs

- [x] 11.1 Update `server/README.md` (or top-level README) with the new layout, env vars, and migration commands
- [x] 11.2 Note `/api/v1/` prefix expectation in `cli/README.md`
