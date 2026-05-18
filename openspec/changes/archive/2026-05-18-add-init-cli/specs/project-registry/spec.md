## ADDED Requirements

### Requirement: List projects endpoint
The system SHALL expose `GET /projects` returning a JSON array of objects describing every known project. Each object SHALL include `slug` and `created_at`.

#### Scenario: List returns known projects
- **WHEN** a client GETs `/projects` after two projects have been auto-registered
- **THEN** the response is HTTP 200 and a JSON array of length 2 with both slugs present

#### Scenario: Empty hub
- **WHEN** a client GETs `/projects` with no projects yet registered
- **THEN** the response is HTTP 200 and a JSON array of length 0

### Requirement: Explicit project creation endpoint
The system SHALL expose `POST /projects` accepting a JSON body `{ "slug": "<kebab-case>" }` and creating the project row. The endpoint SHALL return 201 with the created project on success and 409 if the slug already exists. Slugs SHALL be validated as `^[a-z0-9][a-z0-9-]*$`; invalid slugs SHALL be rejected with 400.

#### Scenario: New project created
- **WHEN** a client POSTs `{ "slug": "my-app" }` to `/projects` and `my-app` does not exist
- **THEN** the response is HTTP 201 and the project is inserted

#### Scenario: Duplicate rejected
- **WHEN** a client POSTs `{ "slug": "existing" }` and `existing` already exists
- **THEN** the response is HTTP 409 and no row is changed

#### Scenario: Invalid slug rejected
- **WHEN** a client POSTs `{ "slug": "Bad Slug!" }`
- **THEN** the response is HTTP 400 and no row is created
