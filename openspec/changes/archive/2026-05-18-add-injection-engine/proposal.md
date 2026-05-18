## Why

Once the logging spike (`add-hook-logging-spike`) has surfaced what Claude Code actually sends, we need to turn the hub from a passive logger into the thing that earns the project's name: a push-based context injector. This change builds the minimum viable injection engine — projects, skills, rules, and event handlers — so we can validate the core thesis that *scoped, deterministic, hook-driven* context beats AGENTS.md accumulation and MCP pull.

## What Changes

- Introduce a `project` concept on the hub: a slug, a set of skills, and a set of rules. Projects are auto-registered the first time a hook from an unknown slug arrives.
- Introduce `skill` records: id + name + description + markdown body. Stored server-side only; no skill content lives in the repo.
- Introduce `rule` records keyed to a project, with `on`, optional `match` (glob), and `inject` (skill ids). Rules are managed via HTTP API (UI deferred).
- Implement four real injection events: `SessionStart`, `UserPromptSubmit`, `PreToolUse:Edit|Write`, `PreToolUse:Read`.
- `SessionStart` returns a *map* (skill/doc names + short descriptions + rule count) rather than full content.
- `UserPromptSubmit` performs keyword matching against the user's prompt to select skills to inject.
- `PreToolUse:Edit|Write` fires path-matched rules and injects matching skills.
- `PreToolUse:Read` injects only when explicitly opted in by a rule AND deduped per `(session_id, rule_id)`.
- Track per-session dedupe state in SQLite; clear it on `PostCompact`.
- Add a `.knct/config.toml` file in the repo holding only the project slug and hub URL.
- Update `.claude/settings.json` so hook responses are consumed (no longer always `{}`); add `PostCompact` to the wired events.
- **BREAKING** (vs the spike): the `/hook` endpoint now returns `hookSpecificOutput.additionalContext` payloads, not empty objects. Spike-era assumptions no longer hold.

## Capabilities

### New Capabilities
- `project-registry`: identify projects by slug, auto-register on first contact, store per-project skills and rules.
- `skill-store`: CRUD for skill records (id, name, description, markdown body) over HTTP.
- `rule-engine`: evaluate rules against incoming hook events; support `on`, `match` (glob), `inject`, per-session dedupe; reset on compaction.
- `context-injection`: shape responses to Claude Code's hook protocol (`hookSpecificOutput.additionalContext`) for `SessionStart`, `UserPromptSubmit`, `PreToolUse`.
- `session-map`: build and return the SessionStart "map" — the index of what the hub can offer this session.

### Modified Capabilities
- `hook-logging`: continue logging every event, but now also log the response payload (what was injected) for observability.

## Impact

- Schema additions in `~/.knct/hub.db`: `projects`, `skills`, `rules`, `session_dedupe` tables. Existing `traces` table extended with a `response` column.
- New HTTP endpoints: `POST/GET/PUT/DELETE /projects/{slug}/skills`, `/projects/{slug}/rules`.
- Repo footprint gains `.knct/config.toml` (~3 lines).
- Latency budget: `SessionStart` and `PreToolUse` are blocking — keep handlers under ~50ms in-process work plus negligible SQLite.
- Sensitive content (skill bodies, prompt text) flows through the hub. Still local-only; auth/remote remain out of scope.
- This change does not yet add: modes, opencode support, remote hub, web UI, MCP pull, Langfuse integration.
