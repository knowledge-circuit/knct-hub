## ADDED Requirements

### Requirement: Plugin captures loaded context chunks at session start
The plugin SHALL register a `SessionStart` hook that enumerates every context chunk loaded into the session — CLAUDE.md files, skill descriptions, MCP tool lists, and kpatches — and records for each chunk a content hash, token count, source descriptor, and extracted identifier set.

#### Scenario: Session starts with CLAUDE.md and one MCP server loaded
- **WHEN** Claude Code starts a session with one CLAUDE.md file and one MCP server providing a tool list
- **THEN** the plugin writes a `session_start` JSONL record containing one chunk entry for the CLAUDE.md file and one chunk entry for the MCP tool list, each with `hash`, `token_count`, `source.kind`, `source.label`, and `identifiers` populated

#### Scenario: Token counter unavailable
- **WHEN** the plugin cannot access an exact tokenizer at session start
- **THEN** the `session_start` record sets `token_count_estimated: true` and uses the documented approximation, and downstream reports surface the estimation flag

### Requirement: Plugin records mechanical reference signals per chunk
The plugin SHALL record, for each loaded chunk in a session, whether any of the following reference signals fired: tool-call attribution, identifier match against the union of user prompt / assistant output / tool-call arguments, or keyword match against chunk-declared trigger keywords. Each fired signal SHALL be recorded with its kind; signals SHALL NOT be collapsed into a single boolean.

#### Scenario: MCP tool invoked during session
- **WHEN** a session loads an MCP server's tool list chunk and the assistant calls a tool from that server
- **THEN** the `session_end` record marks that chunk with a reference of kind `tool_call_attribution`

#### Scenario: Identifier from chunk appears in assistant output
- **WHEN** a loaded chunk contains the identifier `pnpm install` and the assistant output for the session contains the string `pnpm install`
- **THEN** the `session_end` record marks that chunk with a reference of kind `identifier_match`

#### Scenario: No signals fire
- **WHEN** a chunk is loaded but no tool-call, identifier, or keyword signal fires before session end
- **THEN** the `session_end` record contains an entry for the chunk with an empty `references` array

### Requirement: Plugin persists session records as append-only JSONL
The plugin SHALL append exactly two JSON records per session — one `session_start` and one `session_end` — to a configurable local log path (default `~/.claude/knct-usage/sessions.jsonl`). Each record SHALL include a `schema_version` field and a stable `session_id` linking the two records.

#### Scenario: Two records per completed session
- **WHEN** a session starts and later ends via the `Stop` hook
- **THEN** the JSONL log gains exactly two new lines sharing the same `session_id`, the first with `record: "session_start"` and the second with `record: "session_end"`

#### Scenario: Session terminates without Stop hook firing
- **WHEN** a session ends abnormally and the `Stop` hook does not fire
- **THEN** the JSONL log contains the `session_start` record but no matching `session_end` record, and the reporter ignores sessions without a `session_end`

### Requirement: Plugin does not persist raw prompts or assistant output
The plugin SHALL NOT write user prompt text, assistant output text, or tool-call argument text verbatim to the JSONL log or any other on-disk artifact. Reference matching SHALL occur in memory; only categorical outcomes (which signals fired against which chunks) SHALL be persisted.

#### Scenario: Prompt contains a secret string
- **WHEN** a user submits a prompt containing the string `sk-test-secret-token`
- **THEN** no record written to `sessions.jsonl` for that session contains the substring `sk-test-secret-token`

### Requirement: Plugin bounds local storage growth
The plugin SHALL enforce retention by trimming the JSONL log at report time to at most a configured maximum number of sessions (default 500) or a configured maximum file size (default 50 MB), whichever limit is reached first. Trimming SHALL preserve the most recent sessions.

#### Scenario: Log exceeds session cap at report time
- **WHEN** the JSONL log contains 600 completed sessions and the configured cap is 500, and a report is requested
- **THEN** the plugin trims the log so that exactly the 500 most recent sessions remain, and proceeds to render the report from the trimmed log

### Requirement: Reporter exposes per-chunk load and reference counts on demand
The plugin SHALL provide a CLI command and a matching Claude Code slash command that read the JSONL log and emit a per-chunk report including chunk label, short hash, load count, reference count, references broken down by signal kind, tokens per load, and total token cost across the window. The report SHALL NOT collapse these into a single composite score.

#### Scenario: Reporter run on a populated log
- **WHEN** the user runs the reporter CLI against a log containing chunks with varying load and reference counts
- **THEN** the output lists each chunk with its label, short hash, load count, reference count, per-kind reference breakdown, tokens per load, and total tokens, sorted by the configured sort key

#### Scenario: Machine-readable output requested
- **WHEN** the user runs the reporter CLI with `--json`
- **THEN** the reporter emits a JSON document containing the same per-chunk fields and a top-level `schema_version`, suitable for later aggregation

### Requirement: Plugin fails safe on hook schema mismatch
The plugin SHALL detect when the Claude Code hook payload schema does not match a supported version, log a single warning line, and disable capture for the remainder of the session rather than writing records that may be malformed.

#### Scenario: Unsupported hook payload encountered
- **WHEN** the plugin receives a hook payload whose schema version is outside its supported range
- **THEN** the plugin logs one warning line identifying the mismatch, writes no `session_start` or `session_end` record for that session, and does not raise an error that interrupts the Claude Code session
