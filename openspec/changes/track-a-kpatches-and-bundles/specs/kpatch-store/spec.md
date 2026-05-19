## ADDED Requirements

### Requirement: Kpatch record shape
The system SHALL store kpatches with fields `id` (kebab-case string, unique within an org), `org_id`, `name`, `description` (one line), `body` (markdown text), and `keywords` (array of strings). A kpatch SHALL be owned by exactly one org.

#### Scenario: Kpatch persisted with all fields
- **WHEN** a client PUTs a kpatch with id, name, description, body, and keywords under an org
- **THEN** all fields are persisted under `(org_id, id)` and retrievable via GET

### Requirement: Kpatch CRUD endpoints
The system SHALL expose `GET`, `PUT`, and `DELETE` endpoints under `/api/v1/orgs/{org}/kpatches` and `/api/v1/orgs/{org}/kpatches/{id}` for managing kpatches. Mutating endpoints SHALL require the caller's role on the org to be Owner or Admin.

#### Scenario: Create or replace kpatch
- **WHEN** an Admin PUTs `/api/v1/orgs/acme/kpatches/commit-conventions` with a JSON body
- **THEN** the kpatch is upserted and the server responds with HTTP 200

#### Scenario: Member cannot mutate
- **WHEN** a Member attempts to PUT or DELETE a kpatch under their org
- **THEN** the server responds with HTTP 403 and no state changes

#### Scenario: List kpatches for an org
- **WHEN** a client GETs `/api/v1/orgs/acme/kpatches`
- **THEN** the server returns a JSON array of all kpatches belonging to that org

#### Scenario: Delete kpatch
- **WHEN** an Admin DELETEs `/api/v1/orgs/acme/kpatches/commit-conventions`
- **THEN** the kpatch is removed and subsequent GET returns 404
- **AND** all triggers pointing to that kpatch are also removed

### Requirement: Kpatch id immutable
The `id` of a kpatch SHALL be immutable after creation. Renaming SHALL be modeled as delete + create by the client.

#### Scenario: PUT to new id creates a new kpatch
- **WHEN** a client PUTs a kpatch to `/api/v1/orgs/acme/kpatches/new-id` whose body originally lived at `old-id`
- **THEN** a new kpatch record is created at `new-id` and `old-id` is untouched
