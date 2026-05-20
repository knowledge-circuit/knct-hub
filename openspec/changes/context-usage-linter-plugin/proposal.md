## Why

knct-hub and kpatches presuppose that injected context (CLAUDE.md, skills, MCP tool lists, kpatches themselves) is worth patching, but today there is no data-backed way to tell which chunks earn their tokens and which are dead weight. Without a falsifiable signal, kpatch authoring is intuition-driven and the hub's value proposition ("manage your context") rests on vibes. A small, local, plugin-only linter that reports load-vs-reference counts per chunk gives users their first honest answer to "what in my context is actually being used?" — and is cheap enough to ship and falsify before committing to any hub-side infrastructure.

## What Changes

- Add a Claude Code plugin that registers hooks (`SessionStart`, `PreToolUse`, `UserPromptSubmit`, `Stop`) to capture, per session: which context chunks were loaded (with content hash + token count) and which mechanical reference signals fired against them.
- Define "reference" mechanically only — no LLM judge, no semantic scoring:
  - MCP tool call → that server's tool-list chunk is referenced.
  - Skill invocation → that skill's description chunk is referenced.
  - Identifier / file-path / keyword from a chunk appears in the user prompt, assistant output, or tool-call arguments.
- Append one JSON line per session to a local log (default `~/.claude/knct-usage/sessions.jsonl`).
- Add a CLI command (and matching slash command) that reads the log and prints a per-chunk report: load count, reference count, tokens per load, total token cost over the window. No single "pollution score" — just the raw counts and cost.
- Explicitly out of scope for this change: hub upload, team-wide aggregation, per-kpatch/bundle rollups, any LLM-based relevance judgment, continuous dashboards, automatic pruning.

## Capabilities

### New Capabilities
- `context-usage-linter`: Local capture of loaded context chunks and mechanical reference signals from Claude Code hooks, plus an on-demand report of load-vs-reference counts and token cost per chunk over a configurable session window.

### Modified Capabilities
<!-- None. This change is plugin-only and does not modify existing hub specs. Hub-side aggregation is a deliberate follow-up, not part of this change. -->

## Impact

- New plugin package (separate from the hub server and CLI) shipped via the existing plugin distribution path; no changes to `server/` or hub data model.
- New local on-disk artifact: `~/.claude/knct-usage/sessions.jsonl` (path configurable). Plugin must handle log rotation or size bounds to avoid unbounded growth.
- No new external dependencies for the hub. Plugin depends only on the Claude Code hook payload schema and a tokenizer for token counts.
- Follow-up (not in this change): hub ingestion endpoint, per-kpatch/bundle usage view, opt-in subscriber telemetry for kpatch authors. Called out here so the design of the JSONL schema anticipates later aggregation without building it now.
