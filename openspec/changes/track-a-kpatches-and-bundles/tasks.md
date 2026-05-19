## 1. Data model & migrations

- [x] 1.1 Author Alembic revision adding tables: `orgs`, `org_members`, `kpatches`, `triggers`, `device_tokens`, `users`
- [x] 1.2 Same revision: add `org_id`, `access_mode`, `members` columns to `projects` (no bundle / disabled / overridden fields)
- [x] 1.3 Same revision: drop `rules` and `skills` tables after exporting snapshot to JSON for ops
- [x] 1.4 Same revision: re-key `session_dedupe` rows to point at the new `triggers.id` (or recreate fresh if migration data is unavailable)
- [x] 1.5 Verify migration up + down on a seeded dev database
- [ ] 1.6 Follow-up revision: collapse to scope-based kpatches — drop `bundles` table, drop `orgs.default_bundles` / `orgs.include_unbundled`, drop `projects.attached_bundles` / `projects.disabled_kpatch_ids` / `projects.overridden_kpatches`; recreate `kpatches` with surrogate `pk_id`, `scope`, `project_slug`, `user_id`, `slug`, `disable`; re-key triggers FK to the new `kpatches.pk_id`. Existing rows migrate as `scope="org"`.

## 2. Engine + protocol

- [x] 2.1 Implement kpatch CRUD endpoints under `/api/v1/orgs/{org}/kpatches` (org scope)
- [x] 2.2 Implement trigger CRUD endpoints under `/api/v1/orgs/{org}/kpatches/{slug}/triggers`
- [x] 2.3 Implement kpatch markdown importer (parser + endpoint + optional default-trigger creation)
- [x] 2.5 Implement org CRUD endpoints and `org_members` management with last-Owner guard
- [x] 2.6 Implement project-access endpoints (`access_mode`, `members[]`) and silent-join logic on hook ingress
- [x] 2.8 Trigger evaluator: consume the resolved kpatch set; case-insensitive `prompt_contains` substring match
- [x] 2.9 Add `UserPromptSubmit` Claude Code hook handler that maps to the new `user_prompt` event end-to-end
- [x] 2.10 Update project auto-registration to scope by caller org and require authentication outside solo mode
- [x] 2.11 Confirm `context-injection` wire shape and `hook-logging` traces still record `payload` + `response` correctly
- [ ] 2.12 Rewrite resolver to scope-based form (`kpatch-resolution` spec): collect at org/project/member scopes, dedupe lowest-wins, drop disabled. Delete bundle-inheritance code.
- [ ] 2.13 Add project-scope CRUD endpoints (`/api/v1/orgs/{org}/projects/{slug}/kpatches/...`) + import endpoint at project scope
- [ ] 2.14 Add member-scope CRUD endpoints (`/api/v1/orgs/{org}/projects/{slug}/members/{user_id}/kpatches/...`) + import endpoint at member scope
- [ ] 2.15 Project + member list endpoints support `?include_inherited=true`, returning rows tagged with origin scope + a flag for "has sibling at this scope"
- [ ] 2.16 Delete bundle code: `services/bundles.py`, `api/bundles.py`, bundle endpoints from `api/orgs.py` (`default-bundles`, `include-unbundled`), bundle fields from `api/projects.py`

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

- [x] 4.1 Org-scope Kpatches page: list / create / edit (already in place; verify still works after scope migration)
- [x] 4.2 Trigger management UI per kpatch (list, create, edit, delete)
- [x] 4.3 Kpatch import UI (Import button + drop area) reusing the preview dialog
- [x] 4.5 Org settings: members + roles
- [x] 4.6 Project settings: access mode toggle, members list (no bundles / disabled / overridden fields)
- [x] 4.7 Community page: browse community kpatches, Import to org (Owner/Admin only)
- [ ] 4.8 Clerk sign-in integration on the dashboard with GitHub OAuth enabled
- [ ] 4.9 Hide team/community surfaces in solo mode (probe server mode at boot)
- [ ] 4.10 Delete Bundles page + nav entry; remove "Default bundles" / "Include unbundled" surfaces; remove "Attached bundles" / "Disabled kpatches" / "Overridden kpatches" surfaces from Project Detail
- [ ] 4.11 Project Kpatches view: show project-scope kpatches plus inherited org-scope kpatches (with origin badge) and a disable toggle that creates/destroys a project-scope sibling row with `disable=true`
- [ ] 4.12 Member Kpatches view ("My kpatches" on a project): same affordances for the current user's member scope, showing inherited org + project rows with disable toggle

## 5. Community library

- [ ] 5.1 Reserve `community` org on first server boot; staff-only write guard
- [ ] 5.2 `GET /api/v1/community/kpatches` open to any authenticated caller (and to solo)
- [ ] 5.3 `POST /api/v1/orgs/{org}/community-imports` — deep-copy a community kpatch and its triggers into the target org at org scope

## 6. Content

- [x] 6.1 Port existing commit-conventions skill into kpatch markdown with default `user_prompt` trigger on "commit"
- [ ] 6.2 Author kpatches: branch-naming, pr-template, migration-safety, debug-first, clarifying-questions, no-coauthor, test-conventions
- [ ] 6.3 Publish the 8 kpatches under the `community` org via the seed import

## 7. Integration + acceptance

- [ ] 7.1 End-to-end test in solo mode: import seed kpatch at org scope, fire `user_prompt` hook, verify trace contains `additionalContext`
- [ ] 7.2 End-to-end test: create a project-scope `disable=true` sibling and verify the org kpatch no longer fires
- [ ] 7.3 End-to-end test: create a member-scope override and verify the lowest-scope row wins
- [ ] 7.4 End-to-end test in cloud mode against a staging hub: `knct login`, configure project, hook with token, verify trace and silent-join
- [ ] 7.5 Acceptance: make a real commit through Claude Code in a knct project; confirm `commit-conventions` fired on `user_prompt` and the commit message matches the expected format without manual prompting; trace shows the injection
