## ADDED Requirements

### Requirement: Community library org
The system SHALL reserve a special org id `community` whose kpatches are read-only to all other orgs. Only knct staff (out-of-band) SHALL be able to publish to the community org in Track A.

#### Scenario: Community org exists at install
- **WHEN** the hub is first deployed
- **THEN** the `community` org exists and is owned by a staff user (cloud) or by the solo user (solo mode)

#### Scenario: Non-staff cannot publish to community
- **WHEN** a non-staff Admin attempts to PUT a kpatch under org `community`
- **THEN** the server responds with HTTP 403

### Requirement: Browse community kpatches
The system SHALL expose `GET /api/v1/community/kpatches` returning all org-scope kpatches owned by the `community` org. This endpoint SHALL be accessible to any authenticated user (and to anyone in solo mode).

#### Scenario: List community kpatches
- **WHEN** any authenticated user GETs `/api/v1/community/kpatches`
- **THEN** the response includes every org-scope kpatch owned by the community org

### Requirement: Import community kpatch into an org
The system SHALL expose `POST /api/v1/orgs/{org}/community-imports` accepting a `kpatch_slug` (or `kpatch_pk_id`) and copying the kpatch plus its triggers into the target org at org scope. Imported records SHALL get fresh ids and the target org's `org_id`. Subsequent updates to the community source SHALL NOT propagate automatically.

#### Scenario: Import copies kpatch and triggers
- **WHEN** an Admin posts `{kpatch_slug: "commit-conventions"}` to their org's community-imports endpoint
- **THEN** a copy of the kpatch and each of its triggers is created under their org at org scope
- **AND** later changes to the community source do not change the imported copy

### Requirement: Dashboard community browser
The dashboard SHALL provide a Community page listing community kpatches with name, description, and an Import button. The Import button SHALL be visible only to Owners and Admins. Imports always land at the target org's org scope; users can then move them to project / member scope manually if desired.

#### Scenario: Member sees library but cannot import
- **WHEN** a Member opens the Community page
- **THEN** the kpatch list is rendered without Import buttons
