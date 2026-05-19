## Why

The hub today stores per-project rules and skills as separate records and exposes them only to a single project at a time. That shape does not support team-shared prompt context, community sharing, or anything resembling org-level defaults. Track A reframes the hub around a single shareable artifact (kpatch), groups them into bundles, and adds the org and auth layers required for cloud use — while keeping a `--solo` startup mode so individual devs can still run `uvx knct-hub` with zero friction.

## What Changes

- **BREAKING** Consolidate `rule-engine`, `skill-store`, and `skill-import` into kpatch-shaped capabilities. A kpatch is one markdown file with frontmatter (`id`, `name`, `description`, `keywords`, optional default `trigger`) and a markdown body. On the server, the body lives on a `kpatch` record and triggers live on N separate `trigger` rows pointing at it — preserving today's "one body, many rules" flexibility.
- **BREAKING** Rename hook event `user_prompt_submit` → `user_prompt`. All other event names unchanged.
- **BREAKING** `.knct/config.toml` shrinks to `project_id` + `hub_url` only. No client-side override / disable layer; all resolution happens server-side.
- Introduce `org` as the container above projects. Orgs own bundles, projects, and members.
- Introduce `bundle` — a named, versioned list of kpatch IDs. Bundles attach to an org (inherited by every project in the org) and/or to specific projects.
- Add project-level controls on top of inheritance: `disabled_kpatch_ids[]` (opt-out) and `overridden_kpatches[]` (project-level redefinition wins).
- Add project access modes: `access_mode: "org"` (default — any org member auto-joins on first hook contact, silent-join) and `"invite_only"` (only `members[]` may connect).
- Add Clerk-backed identity on the hub, `knct login` device-token flow (token stored at `~/.knct/credentials`), and a role model: Owner / Admin / Member.
- Add a `--solo` startup arg that bypasses auth entirely for local single-user use.
- Add a `community-library` capability — public, opt-in bundles that an org admin can import into the org.
- Seed the community library with a `knct-essentials` bundle of 8 starter kpatches.

## Capabilities

### New Capabilities
- `kpatch-store`: storage and CRUD for kpatch records (body + frontmatter metadata), keyed by id and owned by an org.
- `kpatch-import`: parse markdown-with-frontmatter into a kpatch record plus an optional default trigger row on the server.
- `trigger-engine`: server-side evaluator that matches hook events (`session_start`, `user_prompt`, `pre_tool_use`) to triggers and yields the set of kpatch IDs to inject, with per-session dedupe preserved.
- `org-registry`: org entity with id/name/members, plus org-level `default_bundles[]`.
- `bundle-store`: bundle entity (id, name, version, ordered list of kpatch IDs) and CRUD endpoints.
- `bundle-inheritance`: server-side resolver that flattens community → org → project bundles for a given project, applies `disabled_kpatch_ids[]` and `overridden_kpatches[]`, and returns the final ordered set of kpatches for a hook request.
- `project-access`: per-project `access_mode` ("org" | "invite_only"), `members[]`, and the silent-join semantics on first hook contact in "org" mode.
- `auth-clerk`: Clerk integration on the hub for human identity, sign-in, and org membership.
- `device-token`: `knct login` CLI flow that exchanges a browser-completed Clerk auth for a long-lived device token; token storage at `~/.knct/credentials`; sent with every hook request and resolved server-side to user + org.
- `solo-mode`: `--solo` startup arg on the server that disables auth, assumes a single implicit user, and treats the local hub as all-access.
- `community-library`: public, read-only bundle listing and per-org import flow.

### Modified Capabilities
- `rule-engine`: **REMOVED** — superseded by `kpatch-store` + `trigger-engine`. The `user_prompt_submit` event is renamed to `user_prompt`; `once_per_session` semantics migrate onto triggers; rule-to-skill linkage becomes trigger-to-kpatch linkage.
- `skill-store`: **REMOVED** — superseded by `kpatch-store`. Skill records become kpatch records owned by an org rather than a project.
- `skill-import`: **REMOVED** — superseded by `kpatch-import`. The markdown file format is retained for community interop; the importer additionally accepts an optional default `trigger` frontmatter block and creates a matching trigger row on import.
- `project-registry`: projects gain `org_id`, `access_mode`, `members[]`, `disabled_kpatch_ids[]`, `overridden_kpatches[]`, and `attached_bundles[]`. Auto-registration on unknown slug is scoped to the authenticated caller's org (or bypassed in solo mode).

## Impact

- **Database**: new tables for `orgs`, `bundles`, `kpatches`, `triggers`, `device_tokens`, `org_members`, `project_members`; drop / rewrite of existing `rules` and `skills` tables; new columns on `projects`. Requires Alembic migration with explicit data-loss boundary (skills migrate to kpatches by id; rules migrate to triggers).
- **API**: `/api/v1/projects/{slug}/rules` and `/api/v1/projects/{slug}/skills` removed. New endpoints under `/api/v1/orgs`, `/api/v1/orgs/{org}/bundles`, `/api/v1/orgs/{org}/kpatches`, plus project subresources for attached bundles, disabled kpatches, and access settings. Hook endpoint signature gains an `Authorization` header (device token) in cloud mode.
- **CLI**: new `knct login` command; `knct init` updated to write the slimmer `.knct/config.toml`; hook handlers updated to send the device token header.
- **Server**: Clerk SDK dependency, device-token issuance + verification middleware, `--solo` startup flag wired through auth middleware.
- **Dashboard**: kpatch CRUD UI, bundle CRUD UI, org settings, project access settings, community-library browser/import.
- **Content**: 8 seed kpatches authored and published as the `knct-essentials` bundle.
- **Unchanged**: `context-injection` (wire shape), `hook-logging` (traces table), `session-map`, `api-versioning`, `cli-init` (interface), `server-config`, `release-pipeline`.
