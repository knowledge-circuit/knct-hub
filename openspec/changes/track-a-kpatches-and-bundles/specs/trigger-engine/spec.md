## ADDED Requirements

### Requirement: Trigger record shape
The system SHALL store triggers with fields `id` (integer PK), `kpatch_id` (integer foreign key to `kpatches.pk_id`, `ON DELETE CASCADE`), `event` (one of `session_start`, `user_prompt`, `pre_tool_use`), optional `prompt_contains` (array of strings, used only when `event = user_prompt`), optional `path_match` (glob string), and optional `once_per_session` (boolean; defaults to `true` for `pre_tool_use` with `tool_name = Read`, `false` otherwise). Multiple triggers MAY reference the same kpatch.

#### Scenario: Trigger persisted with required fields
- **WHEN** a client creates a trigger with `event: pre_tool_use`, `path_match: "services/payments/**"`, attached to a project-scope kpatch `payments-style`
- **THEN** the trigger is stored with `kpatch_id` set to that kpatch's `pk_id` and is retrievable as part of the kpatch's trigger list

### Requirement: Trigger CRUD endpoints
The system SHALL expose `GET`, `POST`, `PUT`, and `DELETE` endpoints under the kpatch's scope-specific URL for managing triggers, e.g. `/api/v1/orgs/{org}/kpatches/{slug}/triggers` for org-scope kpatches, `/api/v1/orgs/{org}/projects/{slug}/kpatches/{kpatch_slug}/triggers` for project-scope, and the corresponding member-scope path. Mutating endpoints SHALL require Owner or Admin role on the org (or the matching user for member-scope).

#### Scenario: List triggers for an org-scope kpatch
- **WHEN** a client GETs `/api/v1/orgs/acme/kpatches/commit-conventions/triggers`
- **THEN** the server returns all triggers attached to that kpatch

### Requirement: Trigger evaluation
The system SHALL evaluate triggers against each incoming hook event and produce the set of kpatch ids to inject. A trigger SHALL match when its `event` matches the event AND, if `path_match` is defined, the event's relevant path (file_path for tool events, cwd otherwise) matches the glob AND, if `prompt_contains` is defined and the event is `user_prompt`, the prompt string contains at least one of the listed substrings (case-insensitive). Triggers are only evaluated for kpatches in the effective set produced by `kpatch-resolution`.

#### Scenario: Trigger matches by event and path
- **WHEN** a `pre_tool_use` event arrives for tool `Edit` with `file_path: "services/payments/checkout.py"`
- **AND** a trigger exists with `event: pre_tool_use`, `path_match: "services/payments/**"`, attached to kpatch `payments-style` that is in the effective set
- **THEN** `payments-style` is added to the response set

#### Scenario: Trigger excluded by path mismatch
- **WHEN** the file_path does not match a trigger's glob
- **THEN** that trigger contributes nothing

#### Scenario: User prompt substring match (case-insensitive)
- **WHEN** a `user_prompt` event arrives with prompt `"Let's COMMIT this change"`
- **AND** a trigger exists with `event: user_prompt`, `prompt_contains: ["commit"]`, attached to an in-effective-set kpatch `commit-conventions`
- **THEN** `commit-conventions` is added to the response set

### Requirement: Per-session dedupe
The system SHALL ensure that any trigger with `once_per_session: true` fires at most once per `(session_id, trigger_id)` until that session's dedupe state is reset. Dedupe state SHALL be persisted in a `session_dedupe` table keyed on `(session_id, trigger_id)`.

#### Scenario: First Read fires, second is suppressed
- **GIVEN** a `pre_tool_use` trigger for Read on `services/payments/**` with `once_per_session: true`
- **WHEN** the agent's first Read in `services/payments/` arrives this session
- **THEN** the trigger fires and the kpatch is injected
- **WHEN** a second matching Read arrives in the same session
- **THEN** the trigger does not contribute its kpatch
