## ADDED Requirements

### Requirement: All endpoints versioned under /api/v1
Every HTTP endpoint the server exposes SHALL be served under the `/api/v1/` prefix. The server SHALL NOT expose any unprefixed application route. The `/api/v1/` prefix SHALL be applied at the application composition layer (e.g., `include_router(..., prefix="/api/v1")`), not duplicated inside individual routers.

#### Scenario: Hook ingestion lives under /api/v1
- **WHEN** a client POSTs to `/api/v1/hook`
- **THEN** the server processes the event normally

#### Scenario: Unprefixed path rejected
- **WHEN** a client POSTs to `/hook` (no version prefix)
- **THEN** the server responds with HTTP 404

#### Scenario: Resource endpoints carry the prefix
- **WHEN** a client GETs `/api/v1/projects`, `/api/v1/projects/{slug}/skills`, or `/api/v1/projects/{slug}/rules`
- **THEN** the server returns the resource as before

### Requirement: Versioning composition lives at the app layer
The system SHALL compose routers in `app.py` (or equivalent application-composition module) with explicit `/api/v1` prefixes per `include_router` call. Individual router modules SHALL NOT bake their own version prefix into their routes.

#### Scenario: Routers are version-agnostic
- **WHEN** a future major version is introduced
- **THEN** adding `app.include_router(router, prefix="/api/v2")` SHALL be sufficient to mount the same router under a new version without modifying the router file
