## ADDED Requirements

### Requirement: Org record shape
The system SHALL store orgs with fields `id` (kebab-case string, globally unique), `name`, and `created_at`. Orgs do not carry a `default_bundles` or any bundle-attachment field — kpatches that apply across all projects in the org are created directly at org scope (see `kpatch-store`, `kpatch-resolution`).

#### Scenario: Org persisted with required fields
- **WHEN** an authenticated user creates an org with id `acme` and name `Acme Inc`
- **THEN** the org row is stored and retrievable via GET `/api/v1/orgs/acme`

### Requirement: Org membership
The system SHALL track org membership in an `org_members` table keyed by `(org_id, user_id)` with a `role` field that is one of `owner`, `admin`, or `member`. Every org SHALL have at least one Owner at all times.

#### Scenario: Creator becomes Owner
- **WHEN** an authenticated user creates a new org
- **THEN** they are inserted into `org_members` with role `owner`

#### Scenario: Cannot remove last Owner
- **WHEN** an Owner attempts to demote themselves and they are the only Owner
- **THEN** the server responds with HTTP 409 and no role change is applied

### Requirement: Org CRUD endpoints
The system SHALL expose endpoints under `/api/v1/orgs` for create, list (only orgs the caller belongs to), and read; `/api/v1/orgs/{org}` for update and delete. Update and delete SHALL require Owner role. Membership management SHALL be at `/api/v1/orgs/{org}/members`.

#### Scenario: List returns only caller's orgs
- **WHEN** a user GETs `/api/v1/orgs`
- **THEN** the response contains exactly the orgs that include the user in `org_members`
