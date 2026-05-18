## Context

knct-hub aims to inject context into AI coding agents via hooks. Before designing a rules engine, skills storage, or any production server, we want to see how Claude Code's hooks behave on the wire — what payloads arrive, how often, with what latency budget, and how session identity behaves across resume and compaction.

This change is a throwaway-grade observation spike. It produces no production code paths and is expected to be replaced once we know what we want.

## Goals / Non-Goals

**Goals:**
- Capture every hook event Claude Code emits to a single SQLite database, indefinitely, with the raw payload preserved.
- Run as one process on the developer machine with zero configuration beyond `pip install` + `uvicorn`.
- Be easy to query — `sqlite3 ~/.knct/hub.db` and `GET /traces` both work.
- Wire this repo's `.claude/settings.json` to point at the server so day-to-day work in this repo generates traces.

**Non-Goals:**
- Rules engine, skills, projects, slugs, or any concept beyond "log this event".
- Authentication, multi-user, remote access, TLS.
- Injecting context (responses are always `{}`).
- Performance optimization. Spike, not server.
- opencode hook support — Claude Code only.
- Schema migration tooling. If the schema changes, delete the DB.

## Decisions

**FastAPI + uvicorn + stdlib sqlite3.** Chosen over Flask or bare `http.server` because FastAPI's automatic JSON parsing removes boilerplate and uvicorn restarts cleanly during iteration. No ORM — direct SQL keeps the spike honest and the schema visible. SQLAlchemy was considered and rejected as overkill for one table.

**Single global DB at `~/.knct/hub.db`.** Matches the long-term hub-lives-outside-repo principle from `idea.md`. Project-local was considered (would isolate spike data) but rejected because we want one place to query across any repo we eventually wire up.

**One endpoint, one table.** All events POST to `/hook`; the body contains `hook_event_name` which we extract and store alongside the raw payload. Per-event endpoints were considered and rejected — they would require touching server code to add a new event, which defeats the point of an exploratory log.

**Always return `{}`.** Claude Code's HTTP hook protocol accepts 2xx with empty body as "no-op." This keeps the spike side-effect-free: the agent runs exactly as it would without the hub. No risk of the spike corrupting agent behavior.

**Port 8765.** Arbitrary but stable. Easy to remember (`8-7-6-5`), well outside common dev-server ranges.

**No `async: true` on hooks in the spike.** We want to measure realistic latency, including the blocking events. If `PreToolUse` adds noticeable lag, that itself is data worth seeing.

## Risks / Trade-offs

- **DB grows unbounded** → fine for a spike; if it becomes a problem, `rm ~/.knct/hub.db` is the migration plan.
- **Hooks fire when server is down** → Claude Code logs a non-2xx, agent continues. Spike tolerates this; no retry.
- **Schema will change once we learn what matters** → accepted. Schema is intentionally minimal so changes are cheap.
- **Latency from blocking hooks could slow agent turns** → if it does, that is the signal to add `async: true` selectively and is part of what we are measuring.
- **Capturing full payloads may include sensitive content (prompts, file contents)** → accepted for a local-only spike on a developer machine. Documented as a non-goal for production.
