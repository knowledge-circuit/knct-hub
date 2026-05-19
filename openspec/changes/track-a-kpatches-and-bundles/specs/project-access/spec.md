## ADDED Requirements

### Requirement: Access mode field
The system SHALL store on every project an `access_mode` field that is one of `"org"` (default) or `"invite_only"`, and a `members[]` array of user ids.

#### Scenario: Default access mode
- **WHEN** a project is created without an explicit access mode
- **THEN** its `access_mode` is `"org"` and `members[]` is empty

### Requirement: Org access mode allows any org member with silent join
When a project's `access_mode` is `"org"`, the system SHALL allow any user who belongs to the project's `org_id` to issue hook requests against it. On the first successful request from a user not already in `members[]`, the system SHALL add the user to `members[]`.

#### Scenario: Silent join on first hook
- **GIVEN** a project under org `acme` with `access_mode: "org"` and `members: []`
- **WHEN** an authenticated `acme` org member sends a hook for that project
- **THEN** the request is processed AND the user is added to the project's `members[]`

#### Scenario: Non-org user rejected
- **WHEN** an authenticated user who does not belong to the project's org sends a hook for that project
- **THEN** the server responds with HTTP 403 and no rule evaluation runs

### Requirement: Invite-only access mode gates by members list
When a project's `access_mode` is `"invite_only"`, the system SHALL only accept hook requests from users whose id appears in the project's `members[]` (in addition to belonging to the project's org). Silent join SHALL NOT apply.

#### Scenario: Non-member rejected in invite-only
- **GIVEN** a project with `access_mode: "invite_only"` and `members: ["u1"]`
- **WHEN** authenticated user `u2` (also in the org) sends a hook for that project
- **THEN** the server responds with HTTP 403

### Requirement: Access settings endpoints
The system SHALL expose endpoints under `/api/v1/projects/{slug}/access` for reading and updating `access_mode` and `members[]`. Updates SHALL require Owner or Admin role on the project's org.

#### Scenario: Admin toggles to invite-only
- **WHEN** an Admin PUTs `access_mode: "invite_only"` on a project
- **THEN** the new access mode is persisted and subsequent hook requests apply the new rule
