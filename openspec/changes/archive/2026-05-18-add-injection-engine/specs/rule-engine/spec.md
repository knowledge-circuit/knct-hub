## ADDED Requirements

### Requirement: Rule record shape
The system SHALL store rules with fields `id`, `project_slug`, `on` (one of `session_start`, `user_prompt_submit`, `pre_edit`, `pre_read`), optional `match` (glob pattern), `inject` (array of skill ids), and optional `once_per_session` (boolean; defaults to `true` for `pre_read`, `false` otherwise).

#### Scenario: Rule persisted with required fields
- **WHEN** a client creates a rule with `on: "pre_edit"`, `match: "services/payments/**"`, `inject: ["payments-style"]`
- **THEN** the rule is stored under the given project slug

### Requirement: Rule CRUD endpoints
The system SHALL expose `GET`, `POST`, `PUT`, and `DELETE` endpoints under `/projects/{slug}/rules` for managing rules.

#### Scenario: List rules for a project
- **WHEN** a client GETs `/projects/my-app/rules`
- **THEN** the server returns all rules belonging to that project

### Requirement: Rule evaluation
The system SHALL evaluate a project's rules against each incoming hook event and produce a set of skill ids to inject. A rule SHALL match when its `on` matches the event AND, if a `match` pattern is defined, the event's relevant path (file_path for tool events, cwd otherwise) matches the glob.

#### Scenario: Rule matches by event and path
- **WHEN** a `PreToolUse` event arrives for tool `Edit` with `file_path: "services/payments/checkout.py"`
- **AND** a rule exists with `on: "pre_edit"`, `match: "services/payments/**"`
- **THEN** the rule's `inject` skill ids are added to the response set

#### Scenario: Rule excluded by path mismatch
- **WHEN** the file_path does not match a rule's glob
- **THEN** that rule contributes no skills to the response

### Requirement: Per-session dedupe for Read injection
The system SHALL ensure that any rule with `once_per_session: true` fires at most once per `(session_id, rule_id)` until that session's dedupe state is reset. Dedupe state SHALL be persisted in a `session_dedupe` table.

#### Scenario: First Read fires, second is suppressed
- **GIVEN** a `pre_read` rule for `services/payments/**` with `once_per_session: true`
- **WHEN** the agent's first Read in `services/payments/` arrives this session
- **THEN** the rule fires and the `(session_id, rule_id)` pair is recorded
- **WHEN** a subsequent Read in `services/payments/` arrives in the same session
- **THEN** the rule does not fire and no skills are injected for it

### Requirement: Dedupe reset on compaction
The system SHALL clear dedupe state for a session when a `PostCompact` event arrives for that session.

#### Scenario: PostCompact clears state
- **WHEN** a `PostCompact` event arrives with `session_id: "abc"`
- **THEN** all `session_dedupe` rows with `session_id = "abc"` are deleted
- **AND** subsequent matching events re-fire previously-deduped rules
