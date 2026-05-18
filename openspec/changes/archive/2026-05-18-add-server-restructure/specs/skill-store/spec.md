## MODIFIED Requirements

### Requirement: Skill CRUD endpoints
The system SHALL expose `GET`, `PUT`, and `DELETE` HTTP endpoints under `/api/v1/projects/{slug}/skills` and `/api/v1/projects/{slug}/skills/{id}` for managing skills.

#### Scenario: Create or replace skill
- **WHEN** a client PUTs `/api/v1/projects/my-app/skills/payments` with a JSON body
- **THEN** the skill is upserted and the server responds with HTTP 200

#### Scenario: List skills for a project
- **WHEN** a client GETs `/api/v1/projects/my-app/skills`
- **THEN** the server returns a JSON array of all skills belonging to that project

#### Scenario: Delete skill
- **WHEN** a client DELETEs `/api/v1/projects/my-app/skills/payments`
- **THEN** the skill is removed and subsequent GET returns 404
