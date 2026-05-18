## 1. Monorepo restructure

- [x] 1.1 `git mv pyproject.toml uv.lock src server/` and update `pyproject.toml` package discovery paths if needed
- [x] 1.2 Update README install/run commands to reflect new server location (`uv run --directory server python -m knct_hub`)
- [x] 1.3 Verify the server still starts and `/traces` works from the new location

## 2. Server: list and create endpoints

- [x] 2.1 Add `GET /projects` returning `[{slug, created_at}, ...]` ordered by `created_at` ASC
- [x] 2.2 Add `POST /projects` accepting `{slug}`; validate slug pattern; insert and return 201, or 409 on duplicate
- [x] 2.3 Add a curl smoke test confirming list + create + duplicate-409 paths

## 3. CLI scaffold

- [x] 3.1 Create `cli/package.json` with `name: "@knct/cli"`, `bin: { "knct": "./dist/cli.js" }`, `type: "module"`, Node ≥20 engines
- [x] 3.2 Create `cli/tsconfig.json` targeting ES2022, NodeNext modules, strict
- [x] 3.3 Add dev deps: `typescript`, `tsx`, `esbuild`, `@types/node`; runtime deps: `@inquirer/prompts`, `@iarna/toml`
- [x] 3.4 Add npm scripts: `dev` (tsx), `build` (esbuild bundle → `dist/cli.js` with shebang), `pack:dry` (npm pack dry-run)

## 4. knct init implementation

- [x] 4.1 Implement argv parser supporting `--hub <url>` and `--help`
- [x] 4.2 Implement `resolveHubUrl()` — flag wins; else prompt with default `http://localhost:8765`
- [x] 4.3 Implement `fetchProjects(hubUrl)` calling `GET /projects`; surface clean error on connection failure
- [x] 4.4 Implement the interactive picker — `<Create new>` first, then existing slugs alphabetical
- [x] 4.5 Implement create-flow: prompt for slug (default = kebab(basename(cwd))), POST `/projects`, handle 409 by re-prompting
- [x] 4.6 Implement `writeKnctConfig(slug, hubUrl)` — overwrite `.knct/config.toml` using `@iarna/toml`
- [x] 4.7 Implement `writeClaudeSettings(slug, hubUrl)` — overwrite `.claude/settings.json` with the six hook entries and `X-Project-Slug` header
- [x] 4.8 Implement completion summary output

## 5. Validation

- [x] 5.1 `npm run build` in `cli/` produces a runnable `dist/cli.js`
- [x] 5.2 In a scratch directory, `node /path/to/cli/dist/cli.js init --hub http://localhost:8765` completes end to end against the running hub
- [x] 5.3 Re-running `init` over existing config overwrites cleanly
- [x] 5.4 With the hub stopped, `init` fails with a clear error message

## 6. Docs

- [x] 6.1 Add `cli/README.md` documenting `npx @knct/cli init`, the `--hub` flag, and what files are written
- [x] 6.2 Update top-level `README.md`: monorepo layout, link to `server/` and `cli/` READMEs
- [x] 6.3 Document the publish flow (`npm pack`, `npm publish --access public`) without actually publishing
