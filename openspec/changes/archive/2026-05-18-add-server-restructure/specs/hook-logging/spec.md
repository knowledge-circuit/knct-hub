## MODIFIED Requirements

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

### Requirement: Trace inspection endpoint
The system SHALL expose an HTTP `GET /api/v1/traces` endpoint that returns recent hook events as JSON, most-recent first.

#### Scenario: Recent events returned
- **WHEN** a client requests `GET /api/v1/traces`
- **THEN** the server responds with HTTP 200 and a JSON array of stored events ordered by timestamp descending

#### Scenario: Limit parameter respected
- **WHEN** a client requests `GET /api/v1/traces?limit=10`
- **THEN** the server returns at most 10 events
