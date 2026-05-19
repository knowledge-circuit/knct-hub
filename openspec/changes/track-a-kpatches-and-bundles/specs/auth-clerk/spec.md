## ADDED Requirements

### Requirement: Clerk-backed identity
The system SHALL use Clerk as the identity provider for the hub in cloud mode. Every authenticated request SHALL resolve to a Clerk user id, which the hub SHALL map to an internal `users` row keyed by `clerk_id`.

#### Scenario: New Clerk user provisioned on first sign-in
- **WHEN** a request arrives carrying a valid Clerk session for a user with no existing `users` row
- **THEN** the server inserts a `users` row with the Clerk id and proceeds with the request

### Requirement: Dashboard sign-in flow
The dashboard SHALL use Clerk's hosted sign-in UI for sign-up, sign-in, and sign-out. The dashboard SHALL NOT implement its own credential UI.

#### Scenario: Unauthenticated dashboard request redirects
- **WHEN** an unauthenticated user opens any authenticated dashboard route
- **THEN** the user is redirected to the Clerk sign-in page

### Requirement: GitHub OAuth supported
The Clerk configuration SHALL enable GitHub as a sign-in method at minimum. Additional providers MAY be added without spec changes.

#### Scenario: GitHub button present on sign-in
- **WHEN** the sign-in page renders
- **THEN** the GitHub OAuth option is available

### Requirement: Auth bypass under solo mode
When the server is started in solo mode (see `solo-mode`), the system SHALL NOT invoke Clerk for any request; all auth middleware SHALL be skipped and a single implicit user SHALL be assumed.

#### Scenario: Solo mode skips Clerk
- **GIVEN** the server is started with `--solo`
- **WHEN** any request arrives
- **THEN** Clerk is not contacted and the implicit `solo` user is used
