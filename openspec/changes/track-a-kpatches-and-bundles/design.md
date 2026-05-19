## Context

Today's hub is a single-tenant, per-project store of rules and skills. There is no concept of a team, no sharing across projects, and the only override surface is the per-project rule list. Track A is the first step toward the daily-value product: markdown-driven, prompt-aware, team-shared, observable prompt context.

The first iteration of Track A introduced a separate **bundle** abstraction with org-default and project-attached bundle arrays, plus project-level `disabled_kpatch_ids[]` and `overridden_kpatches[]` fields. In practice that model is heavier than a solo dev wants (you must invent a bundle name and version before a kpatch you imported can fire) and less expressive than a team eventually wants (no per-user opt-out). This design collapses all of that into one mechanism: each kpatch carries an explicit **scope** — `org`, `project`, or `member` — and resolution is a simple "lowest scope wins, dropped if disable=true" cascade.

The wire shape to Claude Code (hook in, `additionalContext` out) is already correct and stays; the data model behind it is the part this design reshapes.

## Goals / Non-Goals

**Goals:**
- One markdown artifact (kpatch) that is shareable, importable, and community-friendly while still letting the server attach multiple triggers to the same body.
- Server-side, deterministic resolution of which kpatches fire for a given hook request — flat collection of three scopes, dedupe by slug with member > project > org, drop disabled.
- No "attach" step. Creating a kpatch at a scope is the act of attaching it.
- Per-user opt-outs are first-class: any user can disable or override a team kpatch on a project they participate in.
- A single binary that runs as a local solo hub or as the cloud `hub.knct.dev`, with auth toggled by a startup arg.
- Preserve today's wire protocol (`hookSpecificOutput.additionalContext`) and the `traces` table so observability work already done keeps applying.

**Non-Goals:**
- Bundles. Removed entirely from Track A. A future change may reintroduce bundles as **pure UX sugar** ("saved kpatch sets you can splat into a scope") but they will never be a hard requirement for resolution.
- `mode: skill` runtime (skills written to user filesystem). File format remains SKILL.md-compatible for export, but knct only injects.
- Client-side override / disable layer. `.knct/config.toml` is for identity only.
- Modes (strict/fun/arch), context snapshots, TTL, pinning. Post-MVP.
- opencode hook support. Claude Code path first.

## Decisions

### Scope-based kpatch resolution

Every kpatch row carries a `scope` field with value `"org"`, `"project"`, or `"member"`, plus the discriminators that scope requires (`org_id` always; `project_slug` for project/member; `user_id` for member). The unique key is the 5-tuple `(scope, org_id, project_slug, user_id, slug)`, with empty-string sentinels for the not-applicable discriminators so the SQL UNIQUE works on SQLite.

For a hook on `(caller_org, project_slug, caller_user_id)`:

```
fetch:
  scope=org      AND org_id=caller_org
  scope=project  AND org_id=caller_org AND project_slug=project_slug
  scope=member   AND org_id=caller_org AND project_slug=project_slug AND user_id=caller_user_id

dedupe by slug, winner = lowest scope (member > project > org)
drop winners where disable = true
return the survivors and their triggers
```

This collapses three previously-separate Track A concepts — bundle inheritance, project-level disable, project-level override — into one mechanism: **a kpatch row at a lower scope shadows the same slug at a higher scope**. Override = the lower row has a different body. Disable = the lower row has `disable=true`. No separate arrays.

Alternative considered: keep bundles + add a `member_overrides` table. Rejected — more concepts, more code paths, same outcome.

### Surrogate integer PK on kpatches

Composite PKs that include a `scope` column don't play well with FKs: triggers would need a 5-column composite FK, and SQLite UNIQUE constraints with NULL columns are tricky. A single `pk_id INTEGER PRIMARY KEY AUTOINCREMENT` is cleaner: triggers FK to `pk_id`; the 5-tuple is enforced via a separate UNIQUE constraint with empty-string sentinels.

Alternative considered: UUID PK. Rejected for Track A — no cross-server stable-id requirement; integer is fine.

### File-vs-server kpatch split

The kpatch markdown file is the share/import unit and carries at most **one** default trigger in its frontmatter. It does NOT carry a scope hint — scope is determined by which endpoint you POST the file to (`/orgs/{org}/kpatches/import`, `/orgs/{org}/projects/{slug}/kpatches/import`, or the member variant). The server stores body and triggers separately, and the dashboard can add/edit triggers without touching the body.

### Inject-only

`mode` is dropped. Every kpatch is forced-injection via the hook response. The file format stays compatible with Anthropic's SKILL.md so anyone can lift a kpatch into a local `.claude/skills/` directory by hand, but the hub does not write to user filesystems.

### Server-side-only resolution

The client sends `slug + event + payload + device_token`. The server resolves the three scopes, evaluates triggers, dedupes by session, and returns flattened `additionalContext`. The CLI does not see scope or layer information.

### Event rename `user_prompt_submit` → `user_prompt`

Standardise on `user_prompt` because it reads cleaner in kpatch frontmatter and matches the doc the user invokes. Breaking, but Track A is already a data-model break — taking the rename in the same migration is cheaper than two breaks.

### `--solo` startup arg

Solo mode is a flag passed to the server at start time (`uvx knct-hub --solo` or `KNCT_SOLO=1`). When on:
- auth middleware is bypassed for all requests,
- a single implicit `solo` org and `solo` user are assumed,
- the device-token header is ignored if present,
- the dashboard does not render org/member management surfaces.

Solo mode is also the only environment in which per-user state matters for a single-user setup: member-scope kpatches under `user_id = "solo"` resolve normally.

### Silent join on `access_mode: org`

In cloud mode, when an authenticated user posts a hook with a known slug whose project is in their org, the server adds the user to `project.members[]` if not already present and processes the request normally. This makes the "give a teammate the slug, they're in" flow work without an invite step.

## Risks / Trade-offs

- **Member-scope discoverability.** [Risk] Per-user opt-outs are powerful but invisible to teammates — a user could disable a kpatch and never realize their teammates still see it. → Mitigation: the project kpatch list view shows inherited org kpatches with a clear "you have a member-scope disable" indicator next to each row.
- **Empty-string sentinel in unique key.** [Risk] Using `""` for the not-applicable discriminator is mildly surprising in SQL queries. → Mitigation: encapsulate inside the service layer; no consumer SQL should see the sentinel.
- **Migration is destructive.** [Risk] Bundles + `disabled_kpatch_ids` + `overridden_kpatches` are dropped. → Mitigation: there are no production users; we wipe and re-seed.
- **Solo-mode drift.** [Risk] Code paths that only run under solo mode rot. → Mitigation: solo is a thin auth middleware bypass, not a parallel code path.
- **No bundle = no team curation aid.** [Risk] Teams that want "a named set of kpatches I can apply elsewhere" lose that affordance. → Mitigation: explicitly out of scope for Track A; a future change can layer bundles back in as sugar (saved kpatch slug lists, expand-on-attach so resolution stays predictable).

## Migration Plan

1. Alembic revision adds `orgs`, `org_members`, `users`, `kpatches` (with scope columns + surrogate PK), `triggers`, `device_tokens` tables; adds `org_id`, `access_mode`, `members` to `projects`.
2. The same revision drops `rules` and `skills` tables; the prior Track A revisions are squashed or chained as appropriate. No `bundles` table is created.
3. New release notes call out the break and the `--solo` migration path for self-hosted users (a single-org default is created automatically on first run in solo mode).
4. Cloud hub deploy: bring down hub, run migration, deploy. No staged rollout — there are no external paying users yet.
5. Rollback: keep a JSON snapshot of pre-migration `rules` + `skills` rows; revert image and re-apply the pre-revision schema if needed.

## Open Questions

- Should `triggers` carry an explicit `once_per_session` override per trigger, or is the kpatch-level setting enough? Current spec language inherits today's default (true for `pre_tool_use` Read, false otherwise). Leaning trigger-level for symmetry with how rules worked.
- Community-library publishing model: who can publish to it in Track A? Smallest viable answer is "knct staff only via a seed import" — i.e. the library is read-only for everyone in Track A and a future change adds publishing. Confirm before specs are archived.
- Device-token scope: per-user or per-machine? Per-user is simpler (one token = all your machines); per-machine gives finer revocation. Leaning per-user for Track A.
