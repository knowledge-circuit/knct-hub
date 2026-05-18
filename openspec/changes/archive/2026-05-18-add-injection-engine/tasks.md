## 1. Schema upgrade

- [x] 1.1 Add `projects (slug TEXT PRIMARY KEY, created_at TEXT)` table
- [x] 1.2 Add `skills (id TEXT, project_slug TEXT, name TEXT, description TEXT, body TEXT, keywords TEXT, PRIMARY KEY(project_slug, id))` table
- [x] 1.3 Add `rules (id INTEGER PRIMARY KEY, project_slug TEXT, on_event TEXT, match TEXT, inject TEXT, once_per_session INTEGER)` table with index on `(project_slug, on_event)`
- [x] 1.4 Add `session_dedupe (session_id TEXT, rule_id INTEGER, fired_at TEXT, PRIMARY KEY(session_id, rule_id))` table
- [x] 1.5 `ALTER TABLE traces ADD COLUMN response TEXT` if the column is missing
- [x] 1.6 On startup, prune `session_dedupe` rows older than 30 days

## 2. Project registry

- [x] 2.1 Extract `project_slug` from every incoming hook request; 400 if missing
- [x] 2.2 Implement `ensure_project(slug)` that inserts a row if absent

## 3. Skill store HTTP API

- [x] 3.1 `GET /projects/{slug}/skills` → list
- [x] 3.2 `PUT /projects/{slug}/skills/{id}` → upsert
- [x] 3.3 `DELETE /projects/{slug}/skills/{id}` → delete
- [x] 3.4 `GET /projects/{slug}/skills/{id}` → single skill

## 4. Rule CRUD HTTP API

- [x] 4.1 `GET /projects/{slug}/rules` → list
- [x] 4.2 `POST /projects/{slug}/rules` → create, returns id
- [x] 4.3 `PUT /projects/{slug}/rules/{id}` → update
- [x] 4.4 `DELETE /projects/{slug}/rules/{id}` → delete

## 5. Rule evaluator

- [x] 5.1 Implement `evaluate(slug, event_name, payload) -> [skill_id]` selecting rules by `(project_slug, on_event)` and tool filter
- [x] 5.2 Add glob path matching using `fnmatch` for the `match` field; resolve target path from `tool_input.file_path` (tool events) or `cwd` (others)
- [x] 5.3 Apply `once_per_session` filter against `session_dedupe`; record fires after a successful match
- [x] 5.4 Concatenate matched skill bodies with `\n\n---\n\n` separators

## 6. Event handlers

- [x] 6.1 `SessionStart` → call session-map builder; return `additionalContext` with skill list + rule count, or `{}` if empty
- [x] 6.2 `UserPromptSubmit` → tokenize prompt, intersect against each skill's `keywords`, inject matching bodies
- [x] 6.3 `PreToolUse` with `tool_name ∈ {Edit, Write}` → evaluator with `on = pre_edit`
- [x] 6.4 `PreToolUse` with `tool_name = Read` → evaluator with `on = pre_read` (dedupe defaults on)
- [x] 6.5 `PreToolUse` with other tools → `{}` immediately
- [x] 6.6 `PostCompact` → `DELETE FROM session_dedupe WHERE session_id = ?`

## 7. Response shaping

- [x] 7.1 Helper `inject_response(event_name, markdown)` returning the `hookSpecificOutput` envelope
- [x] 7.2 When evaluator returns an empty set, return `{}` instead of an empty envelope
- [x] 7.3 Log the response body into `traces.response` for every hook

## 8. Repo wiring

- [x] 8.1 Create `.knct/config.toml` with `slug = "knct-hub"` and `hub_url = "http://localhost:8765"`
- [x] 8.2 Update `.claude/settings.json` to send `project_slug` in headers or body (decide during impl, document in design); add `PostCompact` to the wired events

## 9. Manual validation

- [ ] 9.1 Seed one skill and one `pre_edit` rule via `PUT`/`POST`
- [ ] 9.2 Open the repo in Claude Code, edit a matching file, confirm injected markdown shows in the transcript
- [ ] 9.3 Edit the same file again — confirm rule fires again (Edit does not dedupe by default)
- [ ] 9.4 Add a `pre_read` rule, read a matching file twice in one session — confirm injection only on the first
- [ ] 9.5 Trigger compaction (or POST a synthetic `PostCompact`) and re-read — confirm dedupe was reset

## 10. Document

- [ ] 10.1 Update README with: how to create skills, how to create rules, how dedupe works, how to inspect injections via `traces.response`
