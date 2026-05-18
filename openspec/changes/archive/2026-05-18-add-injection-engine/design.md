## Context

The logging spike proves the wire format and event lifecycle. This change turns the hub into a real injector. We now need a project model, a skill store, a rule engine, and per-event handlers that speak Claude Code's `hookSpecificOutput.additionalContext` protocol.

Two design ideas crystallized during exploration and shape this change:

1. **SessionStart pushes a map, not content.** The agent learns *what is available*, not *everything available*. Full skill bodies arrive only when triggered by a more specific event (`UserPromptSubmit`, `PreToolUse`).
2. **`file_enter` is not a real event.** Path-scoped injection collapses to `PreToolUse:Read` (gated, opt-in, per-session dedupe) and `PreToolUse:Edit|Write` (path-matched, always fires).

## Goals / Non-Goals

**Goals:**
- Deterministic, push-based context injection across four events.
- Server-side rules; repo carries identity only.
- Per-session dedupe for Read injection, reset on compaction.
- Auto-register projects on first contact (zero-config onboarding for teammates).
- Keep injection handlers fast enough that blocking hooks don't visibly slow the agent.

**Non-Goals:**
- Semantic search / embeddings. Keyword matching is enough for v1.
- Modes (`strict`, `fun`, `arch`) — post-MVP per `idea.md`.
- opencode hook support — Claude Code only for this change.
- Remote/multi-user hub. Auth, TLS, RBAC all out of scope.
- Web UI for managing skills/rules. HTTP API only; CLI/curl is the UX.
- MCP pull-side fetching. Hub is push-only here.
- Langfuse / external observability. Internal SQLite logs only.

## Decisions

**Project identity = slug, auto-registered.** The repo's `.knct/config.toml` carries one line: the slug. First hook from an unknown slug auto-creates the project row. Teammates clone the repo and just work. Considered: explicit `knct register` step — rejected as friction the project pitch (zero-config onboarding) explicitly disallows.

**Skills stored server-side only.** No skill markdown lives in the repo. Considered: a hybrid where shared skills come from the hub and project-local skills live in the repo — rejected for v1 because it reintroduces the repo-bloat problem the project exists to solve. Can be reconsidered later.

**Rules as rows, not files.** Rules live in SQLite, edited via HTTP API. No TOML in the repo. Considered: TOML-in-repo with sync — rejected; rules become a runtime concern, decoupled from build/release cycles, and the hub stays authoritative.

**Four real events, no virtual ones.** `SessionStart`, `UserPromptSubmit`, `PreToolUse:Edit|Write`, `PreToolUse:Read`. The DSL exposes `on = "pre_edit"` / `on = "pre_read"` as ergonomic aliases that map to `PreToolUse` filtered by tool name. `file_enter` is gone.

**Read injection is opt-in + deduped.** Rules with `on = pre_read` must be explicitly created. The engine maintains `(session_id, rule_id) → fired_at` state in a `session_dedupe` table; a rule fires at most once per session unless reset. Considered: threshold-based ("fire after N reads in path") — rejected as premature; revisit once we have real traces.

**Reset dedupe on `PostCompact`.** When Claude Code compacts context the agent has functionally forgotten the prior reads, so the hub should re-inject. We wire `PostCompact` and clear the `session_dedupe` rows for that `session_id`. Considered: also resetting on `SessionStart` with `source: "compact"` — rejected as redundant; pick one signal.

**Session map content: dumb v0.** SessionStart returns `"This project has N rules and M skills: <name>: <description>, ..."` as plain markdown. No rule listing, no triggers, no MCP-pull instructions. Evaluate after observing whether agents use it. Considered: rule-table-as-map (transparency play) — held back; ship dumb first.

**Keyword match for UserPromptSubmit.** Each skill has a list of trigger keywords (or we derive them from the description). If any keyword appears in the prompt, the skill is a candidate. Considered: embeddings — rejected for v1 (dependency weight, infra). Keyword is good enough to validate the concept.

**Latency target: handler completes in <50ms wall time on a warm DB.** SQLite is local; queries hit indexes on `(slug, on, tool_name)`. If a handler exceeds this in practice we revisit `async: true` selectively, accepting that async handlers cannot inject.

**Schema-on-top, not migration.** This change adds new tables and one column to `traces`. No formal migration tooling; the spike's "delete the DB" stance ends here. We add a one-shot `CREATE TABLE IF NOT EXISTS` block that handles a clean install and a logged-spike-only DB equally.

## Risks / Trade-offs

- **Keyword matching will miss obvious cases** → accepted for v1; the cost of being wrong is "no injection happened," which is the same as today.
- **Per-session dedupe state grows unbounded if sessions never end** → mitigated by clearing rows older than 30 days on startup. Cheap, correct enough.
- **Auto-registration means a typo in a slug creates a phantom project** → accepted; trivial to delete server-side. Worth flagging when a UI exists.
- **Blocking handlers add latency on every hook** → measured during the spike; keep handlers tight; fall back to `async: true` for `PostToolUse`/`Stop` which don't inject.
- **Skill markdown stored as raw text in SQLite, no version history** → accepted for v1; add audit log later if rule churn becomes confusing.
- **`PostCompact` semantics depend on Claude Code's compaction behavior** → if it doesn't fire as expected, dedupe simply stays sticky until the session ends; degrade gracefully.

## Migration Plan

- This change replaces the spike's `/hook` behavior. Anyone running the spike will start receiving non-empty responses; if their `.claude/settings.json` was authored for the spike, no change is needed — Claude Code consumes `hookSpecificOutput` natively.
- Schema upgrade: `ALTER TABLE traces ADD COLUMN response TEXT` on startup if the column is missing. New tables created via `CREATE TABLE IF NOT EXISTS`.
- Repo: add `.knct/config.toml` with the project's slug. Pick a slug now; future changes assume one exists.

## Open Questions

- **Skill keyword source**: explicit field on the skill, or derived from description? Pick after seeing first batch of skills.
- **Should `PreToolUse:Edit` also dedupe per session?** Probably not — style rules want to fire every edit. But worth re-evaluating once we see how chatty Edit-time injection feels.
- **What's the right shape for the session map when there are many skills?** Truncation? Categorization? Defer until skill count > ~10 in practice.
