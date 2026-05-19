## REMOVED Requirements

### Requirement: Rule record shape
**Reason**: Rules are replaced by `triggers` that reference `kpatches`. See `trigger-engine` spec for the new record shape; the `on` field is renamed to `event` and the value `user_prompt_submit` becomes `user_prompt`. The `inject` array is replaced by a single `kpatch_id` foreign key.
**Migration**: For each existing rule, create one trigger row per element of its `inject` array, copying `match` to `path_match` and translating `on` values (`pre_edit`/`pre_read` → `pre_tool_use` with `path_match` retained; `user_prompt_submit` → `user_prompt`). The migration script lives in the same Alembic revision that drops the `rules` table.

### Requirement: Rule CRUD endpoints
**Reason**: Rule endpoints under `/api/v1/projects/{slug}/rules` are removed; triggers now hang off kpatches under their owning org.
**Migration**: Clients must use `/api/v1/orgs/{org}/kpatches/{id}/triggers` (see `trigger-engine`). The CLI's `knct init` will not write any per-project rule files.

### Requirement: Rule evaluation
**Reason**: Replaced by `trigger-engine` evaluation, which adds substring matching on `user_prompt` events and operates on the effective kpatch set from `bundle-inheritance` rather than directly on per-project rules.
**Migration**: No client action required; the new evaluator runs server-side and returns the same `additionalContext` shape via `context-injection`.

### Requirement: Per-session dedupe for Read injection
**Reason**: Dedupe semantics move onto triggers (see `trigger-engine`). Behavior is preserved: triggers with `once_per_session: true` fire at most once per `(session_id, trigger_id)`.
**Migration**: The `session_dedupe` table is reused; rows are re-keyed from `rule_id` to `trigger_id` by the migration script.

### Requirement: Dedupe reset on compaction
**Reason**: The reset behavior is preserved but now applies to trigger dedupe rows. Authoritative description moves to `trigger-engine` (or stays implicit in `session-map`).
**Migration**: None; the reset hook continues to clear all `session_dedupe` rows for the affected session.
