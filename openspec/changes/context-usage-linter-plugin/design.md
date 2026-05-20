## Context

knct-hub exists to help users curate the context their Claude Code sessions load: CLAUDE.md files, skill descriptions, MCP tool lists, and kpatches. Today, the decision of what to keep, prune, or patch is intuition-driven — users (and kpatch authors) have no data on which chunks are actually exercised by their sessions. Prior discussion ruled out an LLM-as-judge "pollution score" because single-turn relevance judging is unreliable, expensive, biased against durable rules that look off-topic until they fire, and produces a number that collapses under audit. The remaining honest signal is mechanical: did a chunk plausibly come into play during the session? That is cheap to capture from Claude Code hooks and falsifiable per chunk.

## Goals / Non-Goals

**Goals:**
- Capture, per Claude Code session, the set of context chunks loaded and the mechanical reference signals that fired against each one.
- Persist this locally as append-only JSONL with a schema that can later be aggregated server-side without re-instrumentation.
- Provide an on-demand report (CLI + slash command) showing load count, reference count, and total token cost per chunk over a configurable session window.
- Be safe to install: zero network calls, bounded disk usage, no impact on session latency beyond hook overhead.

**Non-Goals:**
- Any LLM-based or semantic relevance judging.
- A single composite "pollution score" or quality metric.
- Per-turn dashboards or continuous monitoring UI.
- Hub upload, team aggregation, or per-kpatch/bundle rollups (deliberate follow-up).
- Automatic pruning or rewriting of CLAUDE.md / kpatches.
- Cross-session causal claims ("this chunk caused this outcome").

## Decisions

### Chunk identity = content hash, not file path
Chunks are identified by `sha256(normalized_content)` plus a human-readable label (source file path + section heading when available). Path-based identity breaks when users move files or when the same kpatch is loaded from different locations. Hash-based identity also lets later hub aggregation merge identical chunks across users without coordination.

**Alternative considered:** path + line range. Rejected because edits invalidate ranges and the report becomes noisy across normal authoring.

### "Reference" is a union of mechanical signals, recorded independently
A chunk is referenced in a session if any of:
1. **Tool-call attribution** — chunk is an MCP server's tool list and a tool from that server was called; or chunk is a skill description and that skill was invoked.
2. **Identifier match** — chunk contains an identifier (function name, file path, CLI flag, env var, distinctive multi-word phrase) that appears in the user prompt, assistant output, or any tool-call argument text.
3. **Keyword match** — chunk declares trigger keywords in a frontmatter field (`triggers: [npm, pnpm, package.json]`); a match in prompt/output/tool args fires the reference.

Each signal is recorded with its kind, so reports can later filter ("show me chunks whose only references were keyword matches"). This keeps the metric honest: a chunk that only fires via fuzzy keyword matching looks different from one whose tools were actually called.

**Alternative considered:** single boolean "referenced". Rejected because it hides the signal quality and prevents users from spotting noisy keyword matches.

### Identifier extraction is heuristic and bounded
Extract candidate identifiers from each chunk once at load time: tokens matching `[A-Za-z_][A-Za-z0-9_]{3,}`, file-path-like strings, and quoted phrases ≥ 3 words. Cap at N (e.g., 50) per chunk to bound matching cost. False negatives are acceptable — the report's truth claim is "never mechanically referenced," not "never relevant."

### Hook surface
- `SessionStart`: enumerate loaded context (CLAUDE.md files, skill descriptions from the skills list, MCP tool lists from the tool list). Compute hashes, token counts, extracted identifiers. Write a `session_start` record.
- `UserPromptSubmit`: buffer the prompt text in memory keyed by session id.
- `PreToolUse`: record tool-call attribution and accumulate argument text for identifier matching.
- `Stop`: accumulate final assistant transcript text. At session end, run identifier/keyword matching over the union of prompt + output + tool args against each loaded chunk's extracted identifiers. Emit a `session_end` record with the per-chunk reference signals.

If `Stop` does not fire (crash, kill), the buffered session is lost — acceptable for an MVP signal. A `flush-on-PreToolUse` mode is a future option.

**Alternative considered:** writing per-event records and reconstructing sessions at report time. Rejected for MVP — heavier on disk and harder to reason about. Two-record-per-session (start + end) is simple and aggregation-friendly.

### Storage: JSONL with bounded retention
`~/.claude/knct-usage/sessions.jsonl` (path configurable via plugin setting). Records are append-only. The reporter trims by session count (keep most recent K, default 500) or by file size (default 50 MB), whichever hits first. Trimming happens lazily at report time, not in the hot path.

**Alternative considered:** SQLite. Rejected for MVP — JSONL is trivially inspectable, diffable, and aggregatable later. Move to SQLite only if reporter latency becomes a problem.

### Token counting
Use the same tokenizer Claude Code uses to assemble the system prompt when available; otherwise a documented approximation (e.g., tiktoken `cl100k_base` or a 4-chars-per-token estimate) with the approximation flag recorded in each session record. Reports surface whether counts are exact or estimated.

### Report shape
CLI: `knct usage [--window 500] [--min-loads 5] [--sort cost|loads|unreferenced]`. Columns: label, hash (short), loads, refs, refs-by-kind, tokens/load, total tokens. No composite score. A `--json` flag emits machine-readable output for future hub upload.

Slash command (`/knct-usage`) wraps the same CLI.

### Schema designed for later aggregation
JSONL records include `schema_version`, stable chunk hash, and a `source` block (`{kind: "claude_md"|"skill"|"mcp_tool_list"|"kpatch", id, label}`). When hub-side ingestion lands, the same records ship as-is — no client rework. This is the only forward-looking concession; everything else is deliberately local.

## Risks / Trade-offs

- **Identifier matching is heuristic** → Documented as such; reports label refs by signal kind so users can discount weak signals. False negatives are the conservative direction (under-counts references; a chunk shown as "unreferenced" is the user's call to verify).
- **Durable rules look unreferenced until they fire** → Default window is session-count-based, not time-based, so low-frequency rules accumulate references over time. Reporter shows raw counts, not ratios; the user decides if 1-in-500 justifies the tokens.
- **`Stop` hook not firing loses the session** → Acceptable for MVP. Documented behavior. Adds motivation for a future periodic-flush mode but not blocking.
- **Disk growth** → Bounded by retention policy enforced at report time. Worst case between reports is one session's record, which is small (< 100 KB typical).
- **Privacy** → The JSONL contains chunk hashes, identifiers extracted from context, and reference signal flags. It does NOT contain user prompts or assistant output verbatim. This is a deliberate constraint: matching happens in memory, only the boolean/categorical outcomes hit disk. Documented in plugin README and enforced by code review.
- **Hooks change shape** → Plugin pins a supported Claude Code hook schema version and fails loudly (logs a one-line warning, disables capture) on mismatch rather than silently producing bad data.
- **Scope creep toward hub** → Explicit non-goal here. The JSONL schema accommodates later upload, but no upload code, auth, or endpoint design lands in this change.
