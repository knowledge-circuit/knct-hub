## ADDED Requirements

### Requirement: knct login command
The CLI SHALL provide a `knct login` command that opens a browser to a hub-hosted device-authorization page, polls the hub for completion, and on success writes the returned device token to `~/.knct/credentials` with file mode `0600`.

#### Scenario: Successful login writes credentials
- **WHEN** the user runs `knct login` and completes the browser flow
- **THEN** `~/.knct/credentials` contains the device token and is readable only by the owner

#### Scenario: Cancelled login leaves no credentials
- **WHEN** the user closes the browser before completing the flow
- **THEN** the CLI exits non-zero and `~/.knct/credentials` is not modified

### Requirement: Device token issuance
The hub SHALL expose endpoints to start a device-authorization flow, complete it after Clerk sign-in, and exchange the resulting one-time code for a long-lived device token. Tokens SHALL be stored server-side as a bcrypt hash alongside `user_id`, `created_at`, `last_used_at`, and an optional `revoked_at`.

#### Scenario: Token issued on completion
- **WHEN** the device flow completes for a Clerk-authenticated user
- **THEN** the server returns a new device token, persists its hash with the user id, and sets `created_at` to now

### Requirement: Device token sent on hook requests
The CLI hook handlers SHALL send the device token as `Authorization: Bearer <token>` on every hook request when not in solo mode. The hub SHALL reject requests without a valid token (HTTP 401) in cloud mode.

#### Scenario: Hook with valid token accepted
- **WHEN** a hook request arrives with a header `Authorization: Bearer <valid token>`
- **THEN** the hub resolves the token to a user and proceeds with project resolution

#### Scenario: Hook without token rejected in cloud mode
- **WHEN** a hook request arrives without an `Authorization` header and the server is not in solo mode
- **THEN** the server responds with HTTP 401

### Requirement: Token revocation
The hub SHALL expose `DELETE /api/v1/me/tokens/{token_id}` to revoke a device token. Revoked tokens SHALL be rejected on all subsequent requests.

#### Scenario: Revoked token rejected
- **GIVEN** a device token has been revoked
- **WHEN** a request arrives bearing that token
- **THEN** the server responds with HTTP 401

### Requirement: Last-used tracking
The hub SHALL update `last_used_at` on the device token row each time it successfully authenticates a request, at most once per minute per token.

#### Scenario: Last-used updates
- **WHEN** a token authenticates a request and its `last_used_at` is older than one minute
- **THEN** `last_used_at` is set to the current time
