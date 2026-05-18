## ADDED Requirements

### Requirement: Project identified by slug
The system SHALL identify each project by a unique kebab-case slug. The slug SHALL be supplied by the client in every hook request via a top-level `project_slug` field (set from `.knct/config.toml`).

#### Scenario: Hook request carries slug
- **WHEN** a client POSTs `/hook` with `project_slug: "my-app"`
- **THEN** the server uses `"my-app"` to look up the project record

#### Scenario: Missing slug rejected
- **WHEN** a client POSTs `/hook` without `project_slug`
- **THEN** the server responds with HTTP 400 and persists no rule evaluation

### Requirement: Project auto-registration
The system SHALL create a new project row the first time a hook arrives bearing an unknown slug. No explicit registration step is required.

#### Scenario: Unknown slug registers project
- **WHEN** a hook arrives with `project_slug: "new-app"` and no project row exists
- **THEN** the server inserts a row `{slug: "new-app", created_at: now}`
- **AND** processes the hook against an empty rule set

#### Scenario: Known slug reused
- **WHEN** a hook arrives with `project_slug: "existing-app"` and a row already exists
- **THEN** the server uses the existing row without modification
