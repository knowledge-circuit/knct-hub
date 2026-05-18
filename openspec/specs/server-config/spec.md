# server-config

## Purpose

Provide environment-driven configuration, dual SQLite/Postgres support, and Alembic-managed schema migrations for the hub server.

## Requirements

### Requirement: Settings loaded from environment
The system SHALL load all runtime configuration via a `pydantic-settings`-based `Settings` class that reads values from environment variables and an optional `.env` file. At minimum, the class SHALL expose `database_url`, `host`, `port`, `auto_migrate`, and `log_level`.

#### Scenario: Defaults applied when env is empty
- **WHEN** the server starts with no `KNCT_*` env vars set and no `.env` file
- **THEN** `database_url` defaults to `sqlite+aiosqlite:///<home>/.knct/hub.db`
- **AND** `host` defaults to `127.0.0.1`, `port` defaults to `8765`, `auto_migrate` defaults to `true`

#### Scenario: Env override takes effect
- **WHEN** `KNCT_DATABASE_URL=postgresql+asyncpg://u:p@localhost/knct` is set before startup
- **THEN** the server connects to that Postgres instance

### Requirement: SQLite and Postgres both supported
The system SHALL support SQLite and Postgres as the backing database, selected purely by the `database_url` value. No code path SHALL branch on dialect; all SQL SHALL go through SQLAlchemy.

#### Scenario: SQLite URL connects
- **WHEN** `KNCT_DATABASE_URL` is a `sqlite+aiosqlite://` URL
- **THEN** the server starts, runs migrations, and serves requests against that SQLite file

#### Scenario: Postgres URL connects
- **WHEN** `KNCT_DATABASE_URL` is a `postgresql+asyncpg://` URL pointing at a running Postgres
- **THEN** the server starts, runs migrations, and serves requests against that Postgres database

### Requirement: Alembic-managed migrations
The system SHALL manage schema changes through Alembic migrations stored under `server/alembic/versions/`. Migration files SHALL be generated from SQLModel metadata. The Alembic environment SHALL read the database URL from the same `Settings` source the application uses.

#### Scenario: Migrations directory present
- **WHEN** the repository is checked out fresh
- **THEN** `server/alembic.ini` and `server/alembic/env.py` exist
- **AND** at least one revision file in `server/alembic/versions/` defines the baseline schema

#### Scenario: Auto-migrate on startup
- **GIVEN** `KNCT_AUTO_MIGRATE=true` (the default)
- **WHEN** the server starts against an empty or out-of-date database
- **THEN** `alembic upgrade head` runs as part of the FastAPI lifespan before the first request is served

#### Scenario: Auto-migrate disabled
- **GIVEN** `KNCT_AUTO_MIGRATE=false`
- **WHEN** the server starts
- **THEN** no migrations run automatically and the operator is expected to run `alembic upgrade head` manually
