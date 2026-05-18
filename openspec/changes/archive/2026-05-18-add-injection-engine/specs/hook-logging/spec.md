## MODIFIED Requirements

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
