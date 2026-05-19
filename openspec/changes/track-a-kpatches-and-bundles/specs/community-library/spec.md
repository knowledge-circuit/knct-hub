## ADDED Requirements

### Requirement: Community library org
The system SHALL reserve a special org id `community` whose bundles and kpatches are read-only to all other orgs. Only knct staff (out-of-band) SHALL be able to publish to the community org in Track A.

#### Scenario: Community org exists at install
- **WHEN** the hub is first deployed
- **THEN** the `community` org exists and is owned by a staff user (cloud) or by the solo user (solo mode)

#### Scenario: Non-staff cannot publish to community
- **WHEN** a non-staff Admin attempts to PUT a kpatch or bundle under org `community`
- **THEN** the server responds with HTTP 403

### Requirement: Browse community bundles
The system SHALL expose `GET /api/v1/community/bundles` returning all bundles owned by the `community` org. This endpoint SHALL be accessible to any authenticated user (and to anyone in solo mode).

#### Scenario: List community bundles
- **WHEN** any authenticated user GETs `/api/v1/community/bundles`
- **THEN** the response includes every bundle owned by the community org

### Requirement: Import community bundle into an org
The system SHALL expose `POST /api/v1/orgs/{org}/community-imports` accepting a `bundle_id` and copying the bundle plus all kpatches it references into the target org. Imported records SHALL get fresh `org_id` set to the target org. Subsequent updates to the community source SHALL NOT propagate automatically.

#### Scenario: Import copies bundle and kpatches
- **WHEN** an Admin posts `{bundle_id: "knct-essentials"}` to their org's community-imports endpoint
- **THEN** a copy of the bundle and each referenced kpatch is created under their org
- **AND** later changes to `community/knct-essentials` do not change the imported copy

### Requirement: Dashboard community browser
The dashboard SHALL provide a Community page listing community bundles with name, description, and an Import button. The Import button SHALL be visible only to Owners and Admins.

#### Scenario: Member sees library but cannot import
- **WHEN** a Member opens the Community page
- **THEN** the bundle list is rendered without Import buttons
