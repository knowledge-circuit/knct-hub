## 1. Data model & migrations

- [x] 1.1 Author Alembic revision adding tables: `orgs`, `org_members`, `bundles`, `kpatches`, `triggers`, `device_tokens`, `users`
- [x] 1.2 Same revision: add `org_id`, `access_mode`, `members`, `disabled_kpatch_ids`, `overridden_kpatches`, `attached_bundles` columns to `projects`
- [x] 1.3 Same revision: drop `rules` and `skills` tables after exporting snapshot to JSON for ops
- [x] 1.4 Same revision: re-key `session_dedupe` rows from `rule_id` to `trigger_id` (or recreate fresh if migration data is unavailable)
- [x] 1.5 Verify migration up + down on a seeded dev database

## 2. Engine + protocol

- [x] 2.1 Implement kpatch CRUD endpoints under `/api/v1/orgs/{org}/kpatches`
- [x] 2.2 Implement trigger CRUD endpoints under `/api/v1/orgs/{org}/kpatches/{kpatch_id}/triggers`
- [x] 2.3 Implement kpatch markdown importer (parser + endpoint + optional default-trigger creation)
- [x] 2.4 Implement bundle CRUD endpoints with cross-org reference guard and monotonic version check
- [x] 2.5 Implement org CRUD endpoints and `org_members` management with last-Owner guard
- [x] 2.6 Implement project-access endpoints (`access_mode`, `members[]`) and silent-join logic on hook ingress
- [x] 2.7 Implement bundle-inheritance resolver (community → org → project, dedupe-first, apply disabled and overrides)
- [x] 2.8 Rewrite trigger evaluator to consume the resolved kpatch set; add case-insensitive `prompt_contains` substring match
- [x] 2.9 Add `UserPromptSubmit` Claude Code hook handler that maps to the new `user_prompt` event end-to-end through the resolver and evaluator
- [x] 2.10 Update project auto-registration to scope by caller org and require authentication outside solo mode
- [x] 2.11 Confirm `context-injection` wire shape and `hook-logging` traces still record `payload` + `response` correctly

## 3. Auth + deployment

- [ ] 3.1 Add Clerk SDK dependency on the server and wire middleware that resolves Clerk session to `users` row (auto-provision on first sign-in)
- [ ] 3.2 Implement device-token issuance endpoints (`POST /api/v1/device/start`, completion via Clerk-authed dashboard route, exchange endpoint)
- [ ] 3.3 Implement `Authorization: Bearer` verification middleware for hook endpoints with `last_used_at` write-through (≥1 min throttling)
- [ ] 3.4 Implement `DELETE /api/v1/me/tokens/{token_id}` revocation
- [ ] 3.5 Implement `--solo` startup arg (and `KNCT_SOLO=1`) — bypass Clerk + token middleware, provision `solo` user/org/Owner on first start
- [ ] 3.6 Ensure server fails fast when started without `--solo` and without Clerk credentials configured
- [ ] 3.7 Add `knct login` CLI command — browser open + poll + write `~/.knct/credentials` with mode `0600`
- [ ] 3.8 Update CLI hook handlers to attach `Authorization: Bearer` from `~/.knct/credentials` (skipped in solo)
- [ ] 3.9 Shrink `knct init` to write only `project_id` + `hub_url` in `.knct/config.toml`

## 4. Dashboard

- [x] 4.1 Replace Skills page with Kpatches list/create/edit (org-scoped)
- [x] 4.2 Trigger management UI per kpatch (list, create, edit, delete)
- [x] 4.3 Kpatch import UI (Import button + drop area) reusing the preview dialog
- [x] 4.4 Bundles page: list, create, add/remove kpatches, version field
- [x] 4.5 Org settings: members + roles, default bundles list (Admin+)
- [x] 4.6 Project settings: attached bundles, access mode toggle, members list, disabled kpatches, overridden kpatches
- [x] 4.7 Community page: browse community bundles, Import to org (Owner/Admin only)
- [ ] 4.8 Clerk sign-in integration on the dashboard with GitHub OAuth enabled
- [ ] 4.9 Hide team/community surfaces in solo mode (probe server mode at boot)

## 5. Community library

- [ ] 5.1 Reserve `community` org on first server boot; staff-only write guard
- [ ] 5.2 `GET /api/v1/community/bundles` open to any authenticated caller (and to solo)
- [ ] 5.3 `POST /api/v1/orgs/{org}/community-imports` — deep-copy bundle and referenced kpatches into target org

## 6. Content

- [ ] 6.1 Port existing commit-conventions skill into kpatch markdown with default `user_prompt` trigger on "commit"
- [ ] 6.2 Author kpatches: branch-naming, pr-template, migration-safety, debug-first, clarifying-questions, no-coauthor, test-conventions
- [ ] 6.3 Bundle the 8 kpatches as `knct-essentials` v `1.0.0` under the `community` org via the seed import

## 7. Integration + acceptance

- [ ] 7.1 End-to-end test in solo mode: import seed kpatch, trigger via `user_prompt` hook, verify trace contains `additionalContext`
- [ ] 7.2 End-to-end test in cloud mode against a staging hub: `knct login`, configure project, hook with token, verify trace and silent-join
- [ ] 7.3 Acceptance: make a real commit through Claude Code in a knct project; confirm `commit-conventions` fired on `user_prompt` and the commit message matches the expected format without manual prompting; trace shows the injection
