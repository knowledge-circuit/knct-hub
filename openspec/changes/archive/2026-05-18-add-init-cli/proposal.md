## Why

The hub is useless without a way to wire up a repo, and the spike + injection-engine changes have left that wiring as a manual chore (write `.knct/config.toml` and `.claude/settings.json` by hand, with the right slug and the right header). For teams to adopt knct-hub — the "most value" deployment mode — onboarding has to be one command. This change adds the `knct` CLI, restructures the repo into a monorepo to host both server and CLI side by side, and fills the small server-side gaps the CLI requires (list and explicit-create endpoints for projects).

## What Changes

- **BREAKING (layout)**: restructure the repo into `server/` (current Python code) and `cli/` (new TypeScript package). Update all paths in `.claude/settings.json`, `pyproject.toml`, and run/install instructions in the README.
- Add `GET /projects` to the server: list all known project slugs.
- Add `POST /projects` to the server: create a project with an explicit slug; return 409 if the slug already exists.
- Add a new `cli/` package (`@knct/cli`) with a `knct` bin entry, distributed via npm and runnable through `npx`.
- Implement `knct init`:
  - Resolves the hub URL from a `--hub` flag or interactive prompt (default `http://localhost:8765`).
  - Fetches the existing project list and shows an interactive picker: select an existing project or create a new one (default slug = kebab-cased current directory name).
  - On "create new," `POST /projects` to register.
  - Writes `.knct/config.toml` (slug + hub_url), overwriting if present.
  - Writes `.claude/settings.json` with the six hook events pointing at the hub with the `X-Project-Slug` header, overwriting if present.
  - Prints a summary and a reminder to restart Claude Code.

## Capabilities

### New Capabilities
- `cli-init`: the `knct init` command — interactive linking of a repository to a hub project, with file generation for hooks and config.

### Modified Capabilities
- `project-registry`: add list and explicit-create endpoints (`GET /projects`, `POST /projects`) alongside the existing auto-registration behavior.

## Impact

- Repo layout changes: `pyproject.toml`, `src/knct_hub/`, `uv.lock` move under `server/`. `.claude/settings.json` and `.knct/config.toml` remain at repo root (they describe the *repo*, not the server).
- New top-level `cli/` directory: `package.json`, `tsconfig.json`, `src/cli.ts`, `bin/knct`.
- New tooling expectation for contributors: Node ≥ 20 for the CLI (server contributors remain Python-only).
- New install surface: `npx @knct/cli init` is the recommended entry point for end users. The package is not yet published; this change prepares it for publishing but does not require it.
- The hub HTTP surface gains two endpoints. Existing `/hook` and `/projects/{slug}/...` endpoints are unchanged.
