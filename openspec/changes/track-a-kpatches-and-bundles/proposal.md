## Why

The hub today stores per-project rules and skills as separate records and exposes them only to a single project at a time. That shape does not support team-shared prompt context, community sharing, or anything resembling org-level defaults. Track A reframes the hub around a single shareable artifact (kpatch) that lives at an explicit **scope** — `org`, `project`, or `member` — and is resolved with simple "lowest scope wins" semantics. It also adds the org and auth layers required for cloud use, while keeping a `--solo` startup mode so individual devs can still run `uvx knct-hub` with zero friction.

The earlier draft of Track A introduced a separate **bundle** abstraction with inheritance, attached bundle arrays, project-level disable/override fields, and an "include unbundled" escape hatch. In practice that model was both heavier than a single dev needs and less expressive than a team needs once you want per-user opt-outs. The scope-based model collapses all of that into one mechanism: create a kpatch at the scope where you want it to apply; override/disable by creating a sibling at a lower scope.

## What Changes

- **BREAKING** Consolidate `rule-engine`, `skill-store`, and `skill-import` into kpatch-shaped capabilities. A kpatch is one markdown file with frontmatter (`id`, `name`, `description`, `keywords`, optional default `trigger`) and a markdown body. On the server, the body lives on a `kpatch` record and triggers live on N separate `trigger` rows pointing at it — preserving "one body, many rules" flexibility.
- **BREAKING** Rename hook event `user_prompt_submit` → `user_prompt`. All other event names unchanged.
- **BREAKING** `.knct/config.toml` shrinks to `project_id` + `hub_url` only. No client-side override / disable layer; all resolution happens server-side.
- Introduce `org` as the container above projects. Orgs own kpatches, projects, and members.
- **Each kpatch has an explicit `scope`**: `org` (applies to every project in the org), `project` (applies to one project for all members), or `member` (applies to one user on one project). A kpatch is created or imported *at* a scope — there is no separate "attach" step.
- Resolution is fully server-side and rule-free: for a given hook, the resolver collects all kpatches at the org / project / member scopes for that request, dedupes by slug taking the lowest-scope row, and drops rows where `disable = true`. The result is the effective kpatch set the trigger engine evaluates against.
- "Disable an inherited org kpatch on this project" = create a project-scope kpatch with the same slug and `disable = true`. "Override" = the same but with `disable = false` and a different body / triggers. No separate `disabled_kpatch_ids[]` or `overridden_kpatches[]` arrays.
- No bundles. The `bundle-store` and `bundle-inheritance` capabilities are removed from Track A. (A later change may reintroduce bundles as pure UX sugar — "saved sets of kpatch ids you can splat into a scope" — but they will not be a hard requirement for resolution.)
- Add project access modes: `access_mode: "org"` (default — any org member auto-joins on first hook contact, silent-join) and `"invite_only"` (only `members[]` may connect).
- Add Clerk-backed identity on the hub, `knct login` device-token flow (token stored at `~/.knct/credentials`), and a role model: Owner / Admin / Member.
- Add a `--solo` startup arg that bypasses auth entirely for local single-user use.
- Add a `community-library` capability — public, opt-in import of kpatch markdown files.
- Seed the community library with 8 starter kpatches (`knct-essentials`-style set, but distributed as individual files, not a bundle).

## Capabilities

### New Capabilities
- `kpatch-store`: storage and CRUD for kpatch records, keyed by `(scope, org_id, project_slug, user_id, slug)` with a surrogate integer PK for FK targeting. Body, metadata, and a `disable` flag live on the row.
- `kpatch-import`: parse markdown-with-frontmatter into a kpatch record plus an optional default trigger row on the server. Importer accepts a target scope (org / project / member).
- `trigger-engine`: server-side evaluator that matches hook events (`session_start`, `user_prompt`, `pre_tool_use`) to triggers and yields the set of kpatch ids to inject, with per-session dedupe preserved.
- `kpatch-resolution`: server-side resolver that, given a hook request, returns the effective set of kpatches for `(caller_org, project, caller_user)` by collecting all kpatches at the three scopes, deduplicating by slug with lowest-scope-wins, and dropping rows where `disable` is true.
- `org-registry`: org entity with id/name/members. No `default_bundles` field — direct org-scope kpatches replace it.
- `project-access`: per-project `access_mode` ("org" | "invite_only"), `members[]`, and silent-join semantics on first hook contact in "org" mode.
- `auth-clerk`: Clerk integration on the hub for human identity, sign-in, and org membership.
- `device-token`: `knct login` CLI flow that exchanges a browser-completed Clerk auth for a long-lived device token; token storage at `~/.knct/credentials`; sent with every hook request and resolved server-side to user + org.
- `solo-mode`: `--solo` startup arg on the server that disables auth, assumes a single implicit user, and treats the local hub as all-access.
- `community-library`: public, read-only kpatch listing and per-org import flow (kpatches, not bundles).

### Modified Capabilities
- `rule-engine`: **REMOVED** — superseded by `kpatch-store` + `trigger-engine` + `kpatch-resolution`. The `user_prompt_submit` event is renamed to `user_prompt`; `once_per_session` semantics migrate onto triggers; rule-to-skill linkage becomes trigger-to-kpatch linkage.
- `skill-store`: **REMOVED** — superseded by `kpatch-store`. Skill records become kpatch records owned by an org rather than a project, with explicit scope.
- `skill-import`: **REMOVED** — superseded by `kpatch-import`. The markdown file format is retained for community interop; the importer additionally accepts an optional default `trigger` frontmatter block and a target scope.
- `project-registry`: projects gain `org_id`, `access_mode`, `members[]`. They do **not** gain `attached_bundles[]`, `disabled_kpatch_ids[]`, or `overridden_kpatches[]` — those concerns move onto kpatch records via scope and `disable`. Auto-registration on unknown slug is scoped to the authenticated caller's org (or bypassed in solo mode).

## Impact

- **Database**: new tables for `orgs`, `org_members`, `kpatches` (surrogate PK + scope columns), `triggers`, `device_tokens`, `users`; new columns on `projects` (`org_id`, `access_mode`, `members`); drop / rewrite of existing `rules` and `skills` tables. No `bundles` table. Requires Alembic migrations with explicit data-loss boundary (skills migrate to org-scope kpatches by id; rules migrate to triggers).
- **API**: `/api/v1/projects/{slug}/rules` and `/api/v1/projects/{slug}/skills` removed. New endpoints under `/api/v1/orgs` for org-scope CRUD, `/api/v1/orgs/{org}/projects/{slug}/kpatches` for project-scope CRUD, and `/api/v1/orgs/{org}/projects/{slug}/members/{user}/kpatches` for member-scope CRUD. No bundle endpoints. Hook endpoint signature gains an `Authorization` header (device token) in cloud mode.
- **CLI**: new `knct login` command; `knct init` updated to write the slimmer `.knct/config.toml`; hook handlers updated to send the device token header.
- **Server**: Clerk SDK dependency, device-token issuance + verification middleware, `--solo` startup flag wired through auth middleware.
- **Dashboard**: kpatch CRUD UI with scope-aware lists (project view shows inherited org kpatches alongside its own, with a disable toggle that creates a sibling project-scope row), org settings, project access settings, community-library browser/import.
- **Content**: 8 seed kpatches authored as individual `.md` files in the community library.
- **Unchanged**: `context-injection` (wire shape), `hook-logging` (traces table), `session-map`, `api-versioning`, `cli-init` (interface), `server-config`, `release-pipeline`.
