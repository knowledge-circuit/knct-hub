## 1. Plugin scaffold

- [ ] 1.1 Create new plugin package directory with manifest, README, and license; document the privacy guarantee (no raw prompts/output persisted)
- [ ] 1.2 Add plugin configuration schema: log path (default `~/.claude/knct-usage/sessions.jsonl`), max sessions (default 500), max file size (default 50 MB), supported hook schema version range
- [ ] 1.3 Add tokenizer dependency with documented fallback approximation; expose a `count_tokens(text) -> (count, estimated: bool)` helper

## 2. Hook capture pipeline

- [ ] 2.1 Implement `SessionStart` handler: enumerate loaded CLAUDE.md files, skills, MCP tool lists, and kpatches into chunk records with `hash`, `token_count`, `token_count_estimated`, `source`, and extracted `identifiers`
- [ ] 2.2 Implement identifier extractor (regex-based, capped at N per chunk) and keyword extractor (reads optional `triggers:` frontmatter field)
- [ ] 2.3 Implement `UserPromptSubmit` handler: buffer prompt text in memory keyed by `session_id`
- [ ] 2.4 Implement `PreToolUse` handler: record tool-call attribution against the originating MCP server / skill chunk and accumulate tool-call argument text in memory
- [ ] 2.5 Implement `Stop` handler: run identifier and keyword matching across buffered prompt + assistant output + tool-call args against each loaded chunk; emit `session_end` record with per-chunk references (kind-tagged, never collapsed)
- [ ] 2.6 Implement hook schema version guard: detect mismatch, log one warning line, disable capture for the session, never raise

## 3. Persistence

- [ ] 3.1 Implement append-only JSONL writer for `session_start` and `session_end` records with `schema_version` and shared `session_id`
- [ ] 3.2 Implement lazy retention trim at report time (cap by session count and file size, preserve most recent)
- [ ] 3.3 Add a post-write assertion (test only) that no record contains buffered prompt or output substrings

## 4. Reporter (CLI + slash command)

- [ ] 4.1 Implement CLI `knct usage` with flags `--window`, `--min-loads`, `--sort {cost|loads|unreferenced}`, `--json`
- [ ] 4.2 Aggregate JSONL into per-chunk rows: label, short hash, loads, refs total, refs by kind, tokens/load, total tokens; ignore sessions missing a `session_end`
- [ ] 4.3 Render human-readable table output and machine-readable `--json` output with top-level `schema_version`
- [ ] 4.4 Register matching slash command (`/knct-usage`) that shells out to the CLI

## 5. Tests

- [ ] 5.1 Unit tests for chunk hashing, identifier/keyword extraction, and token counting (including estimated fallback)
- [ ] 5.2 Hook handler tests with synthetic payloads covering: tool-call attribution, identifier match, keyword match, no signals, abnormal termination (no `Stop`)
- [ ] 5.3 Privacy test: feed a session whose prompt and output contain canary strings; assert no canary appears anywhere in the JSONL log
- [ ] 5.4 Retention test: seed > cap sessions, run reporter, assert trim preserves most recent N
- [ ] 5.5 Schema-version-guard test: feed an unsupported hook payload; assert one warning, no records, no exception
- [ ] 5.6 Reporter snapshot tests for table and `--json` output

## 6. Docs and release

- [ ] 6.1 Plugin README: install, configuration, what is and is not captured, privacy guarantee, known limitations (heuristic identifiers, lost sessions on abnormal exit)
- [ ] 6.2 Document the JSONL schema (`schema_version`, record shapes) in a stable location so future hub ingestion can rely on it
- [ ] 6.3 Add a short note in the hub repo pointing at the plugin and explicitly marking hub-side aggregation as the next change, not part of this one
