## Context

The hub server works (engine + CRUD landed in `add-injection-engine`). To turn it into something a team can adopt, every repo needs:

1. A slug identifying the project on the hub.
2. A `.claude/settings.json` wired with the `X-Project-Slug` header pointing at the team's hub URL.

Doing this by hand is error-prone and uninviting. A one-command bootstrapper is the missing piece between "the hub runs" and "the hub is useful."

Two structural pressures shape this change:

1. **Audience asymmetry.** The server is run by one operator per team (or one dev for solo use). The CLI is run by every dev on every repo. They have wildly different install footprints and update cadences, and bundling them together forces a Python dependency on every dev for the sake of writing two config files.
2. **Future scope.** The server is going to grow (auth, web UI, DB beyond SQLite). The CLI will stay small. They will diverge in size, language, and release cadence. Sharing one package now will make every future split painful.

The right answer is a monorepo with `server/` (Python) and `cli/` (TypeScript), shipped as `knct-hub` (PyPI / Docker) and `@knct/cli` (npm) respectively.

## Goals / Non-Goals

**Goals:**
- One-command setup: `npx @knct/cli init` in any repo links it to a hub project.
- Discoverable: list existing projects on the hub and let the user pick instead of guessing slugs.
- Self-contained: `knct init` makes no assumptions about the user's editor or shell config; it writes the two files it needs and that's it.
- Reusable layout: the monorepo split should accommodate adding `web/` (UI) and `opencode/` (plugin) later without further restructuring.

**Non-Goals:**
- Other CLI subcommands (`knct skill`, `knct rule`, `knct status`) — separate, later changes.
- opencode plugin — separate change.
- Authentication or per-project tokens — server is still local-only; the CLI takes no auth. Teams-grade auth lands when the server gains it.
- Merging `.claude/settings.json` with existing user hooks — we overwrite. Users with hand-tuned hook setups can re-add them after `knct init`.
- Publishing `@knct/cli` to npm — we prepare for it but do not flip the switch in this change.
- Migration of `~/.knct/hub.db` — schema is unchanged; existing local DBs keep working.

## Decisions

**Monorepo with `server/` and `cli/` at the root.** The repo is the unit of versioning and reading; splitting now means contributors immediately see "this is a two-component project." Considered: separate repos (`knct/hub`, `knct/cli`) — rejected at this stage because the components are co-evolving fast and one PR often touches both. Can be split later if/when their release cadences truly diverge.

**Server moves under `server/`, repo-level files stay at root.** Specifically, `pyproject.toml`, `src/knct_hub/`, and `uv.lock` move into `server/`. The repo-level `.claude/settings.json`, `.knct/config.toml`, `idea.md`, `openspec/`, and `README.md` remain at the root — they describe the *repo*, not the server. This is the same pattern as Turborepo, Nx, and most Python+JS monorepos.

**CLI is TypeScript on Node ≥ 20.** Reasoning: matches the install pattern users already know from `npx claude-code`, `npx @anthropic-ai/...`, biome, prettier. `npx` is the fastest path to "I tried it." Considered: Python (`uvx knct-cli init`) — rejected because every dev would need uv installed; Go single binary — rejected as overkill and a third language.

**No CLI framework for v1.** `knct init` is one command. Plain `process.argv` parsing with a tiny `parseArgs` helper is enough. Considered: Citty, Commander, oclif — deferred until we have ≥3 subcommands. Adding a framework later is trivial; carrying one now is dead weight.

**Use `@iarna/toml` for TOML writing.** Maintained, well-known, handles edge cases. Considered: `smol-toml` (smaller, modern) — chose `@iarna/toml` for stability since this is a write-only path. Either is fine; not a hill to die on.

**Interactive prompts via `@inquirer/prompts`.** Modular, well-supported, no global state. Considered: `prompts`, `enquirer`, raw readline. `@inquirer/prompts` is the safest default. Non-interactive mode (CI) falls back to flags + dirname-default slug.

**Hub URL: `--hub` flag wins, else prompt with `http://localhost:8765` default.** No environment-variable fallback in v1 — it adds a third source of truth and the flag covers scripted use. Considered: read from a global `~/.knct/config.toml` — deferred; revisit when teams start sharing a single hub URL across many repos.

**Overwrite both files without prompting.** User-stated preference. Both `.knct/config.toml` and `.claude/settings.json` are owned by `knct init`. Considered: prompt-on-existing — rejected as friction. Considered: merge for `.claude/settings.json` — rejected because the merge logic to "replace only knct-owned entries" is fragile, and the user explicitly said replace. If users need other hooks they should add them after init.

**Project picker UX.** GET `/projects` returns the slug list. The picker offers `<Create new>` as the first option, then existing slugs. Selecting create-new prompts for a slug with `kebab(basename(cwd))` as the default. Considered: list + free-form input fallback — the explicit "Create new" entry is clearer.

**Explicit `POST /projects` instead of relying on auto-register.** Auto-register fires on the first `/hook`. For `knct init`, we want the project to exist *before* the first hook so the picker shows it on the next dev's machine without needing a hook in between. Returns 409 if the slug already exists — picker UX prevents this, but a defensive check is cheap.

**No hub auth.** The server still has none. We document this clearly and treat auth as a v0.4-or-later concern. The CLI sends no credentials; it speaks plain HTTP/JSON.

**No publish in this change.** We get the package to a `npm pack`-clean state and document the publish steps in `cli/README.md`, but the actual `npm publish` is a separate, manual operation tied to a real release.

## Risks / Trade-offs

- **Overwriting `.claude/settings.json` may clobber user hooks** → documented in CLI output and README. Users with custom hooks must re-add them after init. Mitigation revisit: ship a `--merge` flag in a follow-up if the complaint surfaces.
- **`npx` runs the latest version by default** → can cache-bust between team members. Mitigation: pin a version in team docs (`npx @knct/cli@0.1.0 init`).
- **Node 20+ requirement excludes ancient setups** → acceptable; Claude Code itself requires modern Node.
- **Two languages in one repo raises the contribution bar** → mitigated by clear `server/` vs `cli/` split and per-component READMEs. Contributors can work in one without touching the other.
- **Server gains two new endpoints without auth** → consistent with the rest of the surface; teams-grade auth is a deliberate later milestone.
- **Restructure breaks any existing local checkouts** → only one machine has this code today. After this change lands, `python -m knct_hub` becomes `cd server && python -m knct_hub` (or `uv run --directory server python -m knct_hub`). Documented in the README.

## Migration Plan

- `git mv` the Python tree into `server/` in one commit.
- Update `.claude/settings.json` URL only if needed (it isn't — hub URL doesn't change).
- Update README to reflect new server start command.
- CLI lands as new files; no existing CLI to migrate.

## Open Questions

- **Node 20 vs 22 minimum?** Pick 20 for broader compatibility; revisit if a feature in 22 becomes useful.
- **Should `knct init` also offer to start the hub if `--hub` points at localhost and the port is dead?** Probably yes long term ("knct hub is not running. Start it now? [Y/n]"), but out of scope for v1.
- **Bundle vs raw TS shipped to npm?** Plan: bundle with esbuild → single `dist/cli.js` so the published package has no transitive ts-node/tsx requirement. Skipped if it becomes friction during impl.
