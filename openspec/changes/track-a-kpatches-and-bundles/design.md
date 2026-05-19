## Context

Today's hub is a single-tenant, per-project store of rules and skills. There is no concept of a team, no sharing across projects, and the only override surface is the per-project rule list. Track A is the first step toward the daily-value product: markdown-driven, prompt-aware, team-shared, observable prompt context. The wire shape to Claude Code (hook in, `additionalContext` out) is already correct and stays; the data model behind it does not.

The change touches almost every domain object — projects gain an org parent, rules and skills are replaced by kpatches and triggers, and a real auth boundary appears for the first time. To keep the door open for individual devs running `uvx knct-hub`, a `--solo` mode must bypass the entire auth stack without bifurcating the codebase.

## Goals / Non-Goals

**Goals:**
- One markdown artifact (kpatch) that is shareable, importable, and community-friendly while still letting the server attach multiple triggers to the same body.
- Server-side, deterministic resolution of which kpatches fire for a given hook request, taking into account community / org / project layers and per-project disables and overrides.
- A single binary that runs as a local solo hub or as the cloud `hub.knct.dev`, with auth toggled by a startup arg.
- Preserve today's wire protocol (`hookSpecificOutput.additionalContext`) and the `traces` table so observability work already done keeps applying.

**Non-Goals:**
- `mode: skill` runtime (skills written to user filesystem). File format remains SKILL.md-compatible for export, but knct only injects.
- Client-side override / disable layer. `.knct/config.toml` is for identity only.
- Cross-org bundle sharing or federation beyond the read-only community library.
- Modes (strict/fun/arch), context snapshots, TTL, pinning. Post-MVP.
- opencode hook support. Claude Code path first.

## Decisions

### File-vs-server kpatch split

The kpatch markdown file is the share/import unit and carries at most **one** default trigger in its frontmatter. The server stores the body on a `kpatches` row and triggers on separate `triggers` rows that foreign-key back. This recovers today's "one skill, many rules" flexibility without making the file format hard to author or copy-paste between orgs.

Alternative considered: 1:1 file-to-rule binding. Rejected because it forces duplicated bodies for any kpatch that should fire on more than one event/path combination.

### Inject-only

`mode` is dropped from the spec. Every kpatch is forced-injection via the hook response. The file format stays compatible with Anthropic's SKILL.md so anyone can lift a kpatch into a local `.claude/skills/` directory by hand, but the hub does not write to user filesystems.

Alternative considered: `mode: inject | skill | both` per kpatch. Rejected — "skill" mode requires owning the user's filesystem (sync, deletion, conflict resolution) which is out of scope for Track A.

### Server-side-only resolution

The client sends `slug + event + payload + device_token`. The server resolves community → org → project bundles, applies `disabled_kpatch_ids[]`, swaps in `overridden_kpatches[]`, evaluates triggers, dedupes by session, and returns flattened `additionalContext`. The CLI does not see the layer graph.

Alternative considered: return layered metadata and let the client filter. Rejected — split-brain bugs and harder migrations. With server-side resolution, the dashboard is the single source of truth.

### Event rename `user_prompt_submit` → `user_prompt`

The existing `rule-engine` spec uses `user_prompt_submit`. Track A standardises on `user_prompt` because it reads cleaner in kpatch frontmatter and matches the doc the user invokes. Breaking, but Track A is already a data-model break for rules — taking the rename in the same migration is cheaper than two breaks.

### `--solo` startup arg

Solo mode is a flag passed to the server at start time (`uvx knct-hub --solo` or `KNCT_SOLO=1`). When on:
- auth middleware is bypassed for all requests,
- a single implicit `solo` org and `solo` user are assumed,
- the device-token header is ignored if present,
- the dashboard does not render org/member management surfaces.

Alternative considered: detect solo from missing Clerk config. Rejected — silently flipping security posture based on absent env vars is dangerous.

### Silent join on `access_mode: org`

In cloud mode, when an authenticated user posts a hook with a known slug whose project is in their org, the server adds the user to `project.members[]` if not already present and processes the request normally. This makes the "give a teammate the slug, they're in" flow work without an invite step.

Risk: a slug typo in `.knct/config.toml` could create a phantom project. Mitigation: auto-register on unknown slug is **scoped to the caller's org** and requires an authenticated caller — solo mode is the only environment where unauthenticated auto-register is allowed.

### Device-token format

Long-lived opaque tokens issued at the end of the `knct login` browser flow, stored as bcrypt hash on the server with `user_id`, `created_at`, `last_used_at`, optional `revoked_at`. Sent as `Authorization: Bearer <token>` on every hook request. No refresh — revoke and re-login.

Alternative considered: short-lived JWTs with refresh. Rejected — hook traffic is high-frequency and unattended; refresh complexity isn't worth it for Track A.

## Risks / Trade-offs

- **Data migration is destructive.** [Risk] Existing `rules` and `skills` rows do not map cleanly when project ownership moves to orgs. → Mitigation: provide a one-shot migration script that lifts existing single-project hubs into a default `solo` org; cloud deployments will be wiped on the breaking release (no production users yet — confirm before shipping).
- **Silent join surface area.** [Risk] Any org member with a guessed slug auto-joins a project. → Mitigation: `access_mode: "invite_only"` for sensitive projects; org membership itself remains gated by Clerk invite.
- **Solo-mode drift.** [Risk] Code paths that only run under solo mode rot. → Mitigation: solo is a thin auth middleware bypass, not a parallel code path; the same handlers run in both modes.
- **kpatch file ambiguity.** [Risk] Users may expect the file's `trigger` to be the single source of truth, but the server can hold more triggers per kpatch. → Mitigation: dashboard surfaces the full trigger list per kpatch; export emits only one canonical trigger and warns when others exist.
- **Performance of the resolver.** [Risk] Flattening community → org → project on every hook request could be slow at scale. → Mitigation: cache resolved kpatch sets per (project, role) tuple with invalidation on bundle/project mutations. Out of scope to implement in Track A but the resolver shape should not preclude it.

## Migration Plan

1. Alembic revision adds `orgs`, `org_members`, `bundles`, `kpatches`, `triggers`, `device_tokens` tables; adds `org_id`, `access_mode`, `members`, `disabled_kpatch_ids`, `overridden_kpatches`, `attached_bundles` to `projects`.
2. Same revision drops `rules` and `skills` tables. A pre-revision script may snapshot them to JSON for ops to keep.
3. New release notes call out the break and the `--solo` migration path for self-hosted users (a single-org default is created automatically on first run in solo mode).
4. Cloud hub deploy: bring down hub, run migration, deploy. No staged rollout — there are no external paying users yet.
5. Rollback: keep the JSON snapshot; revert image and re-apply the pre-revision schema if needed.

## Open Questions

- Should `triggers` carry an explicit `once_per_session` override per trigger, or is the kpatch-level setting enough? Current spec language inherits today's default (true for `pre_read`, false otherwise). Leaning trigger-level for symmetry with how rules worked.
- Community-library publishing model: who can publish to it in Track A? Smallest viable answer is "knct staff only via a seed import" — i.e. the library is read-only for everyone in Track A and a future change adds publishing. Confirm before specs.
- Device-token scope: per-user or per-machine? Per-user is simpler (one token = all your machines); per-machine gives finer revocation. Leaning per-user for Track A.
