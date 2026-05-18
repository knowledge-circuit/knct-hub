# hook-logging

## Purpose

Receive Claude Code hook events over HTTP, persist their raw payloads (and the responses returned to the client) to SQLite, and expose them for inspection.

## Requirements

### Requirement: HTTP hook ingestion endpoint
The system SHALL expose an HTTP `POST /api/v1/hook` endpoint that accepts a JSON body and returns a JSON object with HTTP 200. The endpoint SHALL accept any JSON payload without schema validation.

#### Scenario: Valid hook event accepted
- **WHEN** a client POSTs `{"hook_event_name": "SessionStart", "session_id": "abc", "cwd": "/x"}` to `/api/v1/hook`
- **THEN** the server responds with HTTP 200
- **AND** a row is persisted to the database before the response is returned

#### Scenario: Unknown fields tolerated
- **WHEN** a client POSTs a JSON object containing fields not anticipated by the server
- **THEN** the server responds with HTTP 200 and the full payload is persisted unchanged

#### Scenario: Malformed JSON rejected
- **WHEN** a client POSTs a body that is not valid JSON
- **THEN** the server responds with a 4xx status and no row is persisted

### Requirement: Event persistence to SQLite
The system SHALL persist every successfully received hook event to a SQLite database located at `~/.knct/hub.db`. Each row SHALL include a timestamp, the event name, the session identifier (if present), the working directory (if present), the tool name (if present in the payload), the entire raw payload as JSON text, AND the response body returned to the client as JSON text.

#### Scenario: Database created on first use
- **WHEN** the server starts and `~/.knct/hub.db` does not exist
- **THEN** the parent directory and database file are created automatically with the required schema

#### Scenario: Row contains required columns
- **WHEN** a hook event is persisted
- **THEN** the row contains non-null `ts`, `event`, `payload`, and `response` columns
- **AND** `session_id`, `cwd`, and `tool_name` are populated from the payload when present, or left null otherwise

#### Scenario: Response captured for observability
- **WHEN** a hook fires one or more rules and returns an `additionalContext` body
- **THEN** the `response` column contains the exact JSON the server returned

### Requirement: Trace inspection endpoint
The system SHALL expose an HTTP `GET /api/v1/traces` endpoint that returns recent hook events as JSON, most-recent first.

#### Scenario: Recent events returned
- **WHEN** a client requests `GET /api/v1/traces`
- **THEN** the server responds with HTTP 200 and a JSON array of stored events ordered by timestamp descending

#### Scenario: Limit parameter respected
- **WHEN** a client requests `GET /api/v1/traces?limit=10`
- **THEN** the server returns at most 10 events
