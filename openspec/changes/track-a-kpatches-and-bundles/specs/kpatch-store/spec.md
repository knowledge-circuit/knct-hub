## ADDED Requirements

### Requirement: Kpatch record shape
The system SHALL store kpatches with a surrogate integer primary key (`pk_id`) and the following business fields: `scope` (one of `"org"`, `"project"`, `"member"`), `org_id`, `project_slug` (empty string when `scope = "org"`), `user_id` (empty string when `scope != "member"`), `slug` (kebab-case identifier, unique within a scope tuple), `disable` (boolean, default `false`), `name`, `description` (optional one-liner), `body` (markdown), and `keywords` (array of strings). The combination `(scope, org_id, project_slug, user_id, slug)` SHALL be unique.

#### Scenario: Kpatch persisted with all fields at org scope
- **WHEN** a client creates a kpatch at scope `"org"` with org `acme`, slug `commit-conventions`, and a body
- **THEN** a row is stored with `scope="org"`, `org_id="acme"`, `project_slug=""`, `user_id=""`, `slug="commit-conventions"`, and the body
- **AND** the row is retrievable by its surrogate `pk_id`

#### Scenario: Same slug allowed across scopes
- **GIVEN** a kpatch already exists at `(scope="org", org_id="acme", slug="commit-conventions")`
- **WHEN** a client creates a kpatch at `(scope="project", org_id="acme", project_slug="web", slug="commit-conventions")`
- **THEN** both rows coexist

#### Scenario: Same slug at same scope rejected
- **WHEN** a client attempts to create a second kpatch with the same `(scope, org_id, project_slug, user_id, slug)` as an existing row
- **THEN** the server responds with HTTP 409

### Requirement: Disable flag
The `disable` field SHALL be a boolean. When `true`, the kpatch contributes no triggers and no body at resolution time — its presence in the table exists solely to suppress an inherited row at a higher scope (see `kpatch-resolution`).

#### Scenario: Disable suppresses a body
- **GIVEN** an org-scope kpatch with slug `commit-conventions` and a body
- **WHEN** a project-scope kpatch is created with the same slug and `disable = true` for project `web`
- **THEN** the project-scope row exists with no required body
- **AND** when a hook fires on project `web` the org body is not injected (see `kpatch-resolution`)

### Requirement: Scope-aware CRUD endpoints
The system SHALL expose CRUD endpoints scoped by URL prefix, with mutating endpoints requiring Owner or Admin role on the owning org (member-scope edits also accepted from the user whose `user_id` they target):

- `/api/v1/orgs/{org}/kpatches` and `/api/v1/orgs/{org}/kpatches/{slug}` — org-scope CRUD
- `/api/v1/orgs/{org}/projects/{slug}/kpatches` and `/api/v1/orgs/{org}/projects/{slug}/kpatches/{kpatch_slug}` — project-scope CRUD
- `/api/v1/orgs/{org}/projects/{slug}/members/{user_id}/kpatches` and `/api/v1/orgs/{org}/projects/{slug}/members/{user_id}/kpatches/{kpatch_slug}` — member-scope CRUD

#### Scenario: Create or replace at org scope
- **WHEN** an Admin PUTs `/api/v1/orgs/acme/kpatches/commit-conventions` with a JSON body
- **THEN** the kpatch is upserted at org scope and the server responds with HTTP 200

#### Scenario: Member cannot mutate org-scope
- **WHEN** a Member attempts to PUT or DELETE an org-scope kpatch
- **THEN** the server responds with HTTP 403 and no state changes

#### Scenario: User can edit their own member-scope kpatches
- **WHEN** user `u1` PUTs `/api/v1/orgs/acme/projects/web/members/u1/kpatches/my-prefs`
- **THEN** the request is accepted even if `u1` is not an Admin

#### Scenario: Cascade delete drops triggers
- **WHEN** any kpatch row is deleted
- **THEN** all triggers whose `kpatch_id` foreign-keys to that row's `pk_id` are also deleted

### Requirement: Effective-view endpoint
The project-scope and member-scope list endpoints SHALL accept an optional `?include_inherited=true` query parameter. When set, the response SHALL include kpatches inherited from higher scopes (org for project view; org + project for member view) tagged with their origin scope and an indication of whether the current scope holds a disable / override sibling. The endpoint SHALL NOT mutate any rows.

#### Scenario: Project view shows inherited org kpatches
- **GIVEN** an org-scope kpatch `commit-conventions` exists for org `acme`
- **WHEN** a Member GETs `/api/v1/orgs/acme/projects/web/kpatches?include_inherited=true`
- **THEN** the response includes the org-scope kpatch with a field indicating its origin scope is `"org"`
- **AND** the response indicates the project does not currently hold a sibling row
