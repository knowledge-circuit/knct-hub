## ADDED Requirements

### Requirement: Solo mode startup arg
The server SHALL accept a `--solo` startup arg (or equivalent `KNCT_SOLO=1` environment variable) that switches the process into solo mode for its entire lifetime. Solo mode SHALL NOT be detectable from missing config; it MUST be set explicitly.

#### Scenario: Flag enables solo
- **WHEN** the server is started with `uvx knct-hub --solo`
- **THEN** the process logs that it is running in solo mode and skips Clerk initialization

#### Scenario: Missing Clerk config without flag fails fast
- **WHEN** the server is started without `--solo` and without Clerk credentials configured
- **THEN** the server exits with a non-zero status describing the missing configuration

### Requirement: Implicit solo user and org
On first start in solo mode, the system SHALL ensure exactly one `users` row with id `solo` and one `orgs` row with id `solo`, and that the solo user has Owner role on the solo org. All hook requests under solo mode SHALL be attributed to this user and org.

#### Scenario: Solo user provisioned on first start
- **WHEN** the server is started with `--solo` against an empty database
- **THEN** the `users` table contains the `solo` user, the `orgs` table contains the `solo` org, and `org_members` ties them as Owner

### Requirement: Auth middleware bypassed in solo
In solo mode, the system SHALL bypass authentication for every HTTP request and treat every request as coming from the implicit solo user. Any `Authorization` header SHALL be ignored.

#### Scenario: Hook request without token accepted in solo
- **GIVEN** the server is in solo mode
- **WHEN** a hook request arrives without any `Authorization` header
- **THEN** the request is processed as the solo user

### Requirement: Dashboard hides team surfaces in solo
In solo mode, the dashboard SHALL hide org-management, member-management, role-management, and community-import surfaces. The Kpatches and Bundles surfaces SHALL remain available, operating against the solo org.

#### Scenario: Solo dashboard omits members page
- **WHEN** the dashboard is loaded against a server running in solo mode
- **THEN** the navigation does not link to org members or roles
