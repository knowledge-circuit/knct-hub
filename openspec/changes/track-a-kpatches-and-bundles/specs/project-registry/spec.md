## ADDED Requirements

### Requirement: Project belongs to an org
The system SHALL store an `org_id` foreign key on every project. The `(org_id, slug)` pair SHALL be unique; slugs are not globally unique anymore.

#### Scenario: Same slug allowed across orgs
- **GIVEN** org `acme` has a project with slug `web`
- **WHEN** org `widgets` creates a project with slug `web`
- **THEN** both projects coexist, each scoped to its org

### Requirement: Project access settings persisted
The system SHALL store on every project an `access_mode` (`"org"` | `"invite_only"`, default `"org"`) and a `members[]` array of user ids. Behavior is defined by `project-access`.

#### Scenario: New project defaults to org access
- **WHEN** a new project is created without specifying access settings
- **THEN** its `access_mode` is `"org"` and `members` is empty

### Requirement: Project bundle and override fields
The system SHALL store on every project:
- `attached_bundles[]`: ordered array of bundle ids attached at the project level,
- `disabled_kpatch_ids[]`: array of kpatch ids excluded from injection,
- `overridden_kpatches[]`: array of kpatch records that replace inherited entries by id.

Semantics are defined by `bundle-inheritance`.

#### Scenario: Defaults are empty arrays
- **WHEN** a new project is created
- **THEN** `attached_bundles`, `disabled_kpatch_ids`, and `overridden_kpatches` are all empty arrays

## MODIFIED Requirements

### Requirement: Project identified by slug
The system SHALL identify each project by a kebab-case slug that is unique within its owning org. The slug SHALL be supplied by the client in every hook request via an `X-Project-Slug` HTTP header. The owning org SHALL be resolved from the caller's authenticated identity (or from the implicit solo org in solo mode).

#### Scenario: Hook request carries slug
- **WHEN** an authenticated client POSTs `/api/v1/hook` with header `X-Project-Slug: my-app`
- **THEN** the server uses `(caller_org_id, "my-app")` to look up the project record

#### Scenario: Missing slug rejected
- **WHEN** a client POSTs `/api/v1/hook` without an `X-Project-Slug` header
- **THEN** the server responds with HTTP 400 and persists no rule evaluation

### Requirement: Project auto-registration
The system SHALL create a new project row the first time a hook arrives bearing an unknown slug, scoped to the caller's authenticated org. In solo mode the implicit solo org is used. Auto-registration SHALL NOT occur for unauthenticated requests in cloud mode (which are themselves rejected by `device-token`).

#### Scenario: Unknown slug auto-registers under caller org
- **GIVEN** an authenticated caller belonging to org `acme`
- **WHEN** a hook arrives with `X-Project-Slug: new-app` and no project row exists for `(acme, new-app)`
- **THEN** the server inserts a row with `org_id: acme`, `slug: "new-app"`, `access_mode: "org"`, `created_at: now`
- **AND** processes the hook against an empty effective kpatch set

#### Scenario: Known slug under caller org reused
- **WHEN** a hook arrives with a slug whose row already exists for the caller's org
- **THEN** the server uses the existing row without modification

### Requirement: List projects endpoint
The system SHALL expose `GET /api/v1/orgs/{org}/projects` returning a JSON array of objects describing every known project in the given org. Each object SHALL include `slug`, `org_id`, `access_mode`, and `created_at`. The caller MUST be a member of the org.

#### Scenario: List returns known projects for caller's org
- **WHEN** a Member of org `acme` GETs `/api/v1/orgs/acme/projects` after two projects have been auto-registered
- **THEN** the response is HTTP 200 and a JSON array of length 2 with both slugs present

#### Scenario: Non-member rejected
- **WHEN** a user who does not belong to org `acme` GETs `/api/v1/orgs/acme/projects`
- **THEN** the server responds with HTTP 403
