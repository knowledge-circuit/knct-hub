## ADDED Requirements

### Requirement: Bundle record shape
The system SHALL store bundles with fields `id` (kebab-case, unique within an org), `org_id`, `name`, `version` (semver string), and `kpatch_ids` (ordered array of kpatch ids that MUST belong to the same org as the bundle, except for bundles owned by the community library org).

#### Scenario: Bundle persisted with required fields
- **WHEN** an Admin PUTs a bundle `essentials` v `1.0.0` under org `acme` with three kpatch ids
- **THEN** the bundle is stored and retrievable via GET

### Requirement: Bundle CRUD endpoints
The system SHALL expose `GET`, `POST`, `PUT`, and `DELETE` under `/api/v1/orgs/{org}/bundles` and `/api/v1/orgs/{org}/bundles/{id}` for managing bundles. Mutating endpoints SHALL require Owner or Admin role.

#### Scenario: List bundles for an org
- **WHEN** a Member GETs `/api/v1/orgs/acme/bundles`
- **THEN** the response includes all bundles owned by `acme`

### Requirement: Bundle cross-org kpatch reference rejected
The system SHALL reject any bundle write that references a kpatch id whose `org_id` differs from the bundle's `org_id`, except when the bundle is owned by the community library org (see `community-library`).

#### Scenario: Foreign kpatch rejected
- **WHEN** an Admin attempts to PUT a bundle whose `kpatch_ids` includes a kpatch owned by a different org
- **THEN** the server responds with HTTP 400 and no state changes

### Requirement: Bundle version is monotonic on update
The system SHALL require that any update to a bundle increment its `version` per semver rules. The server SHALL reject updates whose new version is not strictly greater than the stored version.

#### Scenario: Stale version rejected
- **WHEN** an Admin PUTs a bundle with version `1.0.0` over an existing bundle at version `1.0.0`
- **THEN** the server responds with HTTP 409
