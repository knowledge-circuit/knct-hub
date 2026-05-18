## MODIFIED Requirements

### Requirement: Rule CRUD endpoints
The system SHALL expose `GET`, `POST`, `PUT`, and `DELETE` endpoints under `/api/v1/projects/{slug}/rules` for managing rules.

#### Scenario: List rules for a project
- **WHEN** a client GETs `/api/v1/projects/my-app/rules`
- **THEN** the server returns all rules belonging to that project
