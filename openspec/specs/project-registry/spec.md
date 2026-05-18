# project-registry

## Purpose

Identify each project on the hub by a unique slug. Auto-register on first contact, support explicit creation, and expose project listing.

## Requirements

### Requirement: Project identified by slug
The system SHALL identify each project by a unique kebab-case slug. The slug SHALL be supplied by the client in every hook request via an `X-Project-Slug` HTTP header.

#### Scenario: Hook request carries slug
- **WHEN** a client POSTs `/api/v1/hook` with header `X-Project-Slug: my-app`
- **THEN** the server uses `"my-app"` to look up the project record

#### Scenario: Missing slug rejected
- **WHEN** a client POSTs `/api/v1/hook` without an `X-Project-Slug` header
- **THEN** the server responds with HTTP 400 and persists no rule evaluation

### Requirement: Project auto-registration
The system SHALL create a new project row the first time a hook arrives bearing an unknown slug. No explicit registration step is required.

#### Scenario: Unknown slug registers project
- **WHEN** a hook arrives with `X-Project-Slug: new-app` and no project row exists
- **THEN** the server inserts a row `{slug: "new-app", created_at: now}`
- **AND** processes the hook against an empty rule set

#### Scenario: Known slug reused
- **WHEN** a hook arrives with a slug whose row already exists
- **THEN** the server uses the existing row without modification

### Requirement: List projects endpoint
The system SHALL expose `GET /api/v1/projects` returning a JSON array of objects describing every known project. Each object SHALL include `slug` and `created_at`.

#### Scenario: List returns known projects
- **WHEN** a client GETs `/api/v1/projects` after two projects have been auto-registered
- **THEN** the response is HTTP 200 and a JSON array of length 2 with both slugs present

#### Scenario: Empty hub
- **WHEN** a client GETs `/api/v1/projects` with no projects yet registered
- **THEN** the response is HTTP 200 and a JSON array of length 0

### Requirement: Explicit project creation endpoint
The system SHALL expose `POST /api/v1/projects` accepting a JSON body `{ "slug": "<kebab-case>" }` and creating the project row. The endpoint SHALL return 201 with the created project on success and 409 if the slug already exists. Slugs SHALL be validated as `^[a-z0-9][a-z0-9-]*$`; invalid slugs SHALL be rejected with 400.

#### Scenario: New project created
- **WHEN** a client POSTs `{ "slug": "my-app" }` to `/api/v1/projects` and `my-app` does not exist
- **THEN** the response is HTTP 201 and the project is inserted

#### Scenario: Duplicate rejected
- **WHEN** a client POSTs `{ "slug": "existing" }` and `existing` already exists
- **THEN** the response is HTTP 409 and no row is changed

#### Scenario: Invalid slug rejected
- **WHEN** a client POSTs `{ "slug": "Bad Slug!" }`
- **THEN** the response is HTTP 400 and no row is created
