## 1. bump-my-version configs

- [ ] 1.1 Create `server/.bumpversion.toml`: `current_version = "0.0.2"`, `tag_name = "v{new_version}"`, `commit = true`, `tag = true`, `allow_dirty = false`, `commit_args = "-m 'chore: bump server to v{new_version}'"`, file entry pointing at `server/pyproject.toml`'s `version = "..."` line
- [ ] 1.2 Create `cli/.bumpversion.toml`: `current_version = "0.0.1"`, `tag_name = "cli-v{new_version}"`, file entry pointing at `cli/package.json`'s `"version": "..."` line
- [ ] 1.3 Sanity: `uvx bump-my-version bump patch --config-file server/.bumpversion.toml --dry-run --verbose` shows the expected diff without modifying files
- [ ] 1.4 Same for the CLI config

## 2. CLI: migrate to pnpm

- [ ] 2.1 `cd cli && rm package-lock.json && rm -rf node_modules`
- [ ] 2.2 `cd cli && pnpm install` to generate `pnpm-lock.yaml`
- [ ] 2.3 Confirm `pnpm run build` still produces a working `dist/cli.js`
- [ ] 2.4 Update `cli/README.md` to use `pnpm install` / `pnpm run` instead of `npm install` / `npm run`

## 3. Dockerfile: OCI labels

- [ ] 3.1 Add `LABEL org.opencontainers.image.source="https://github.com/knowledge-circuit/knct-hub"` etc. near the top of the runtime stage; allow `org.opencontainers.image.revision` to come from a build arg
- [ ] 3.2 Confirm `docker build .` still succeeds and `docker inspect` shows the labels

## 4. Image workflow

- [ ] 4.1 Create `.github/workflows/image.yml` with triggers `push.branches: [main]` + `push.tags: [v*]` + `workflow_dispatch`
- [ ] 4.2 Steps: `actions/checkout` → `docker/setup-qemu-action` → `docker/setup-buildx-action` → `docker/login-action` (ghcr.io with `github.actor` + `GITHUB_TOKEN`) → `docker/metadata-action` with the tag rules from the design doc → `docker/build-push-action` with `platforms: linux/amd64,linux/arm64`, `cache-from: type=gha`, `cache-to: type=gha,mode=max`, build-args for `revision`
- [ ] 4.3 Set `permissions: { contents: read, packages: write }`
- [ ] 4.4 Use `concurrency: { group: image-${{ github.ref }}, cancel-in-progress: true }` so rapid pushes don't queue up

## 5. CLI publish workflow

- [ ] 5.1 Create `.github/workflows/cli.yml` with trigger `push.tags: [cli-v*]` + `workflow_dispatch`
- [ ] 5.2 Steps: `actions/checkout` → `pnpm/action-setup` → `actions/setup-node@v4` (Node 22, `registry-url: https://registry.npmjs.org`, `cache: pnpm`, `cache-dependency-path: cli/pnpm-lock.yaml`) → `pnpm install --frozen-lockfile` (in `cli/`) → `pnpm run build` → `npm publish --provenance --access public` with `NODE_AUTH_TOKEN: secrets.NPM_TOKEN`
- [ ] 5.3 Set `permissions: { contents: read, id-token: write }` (id-token is required for npm provenance)

## 6. Cut the first releases

- [ ] 6.1 `cd server && uvx bump-my-version bump minor --config-file .bumpversion.toml --new-version 0.1.0` → produces commit + `v0.1.0` tag
- [ ] 6.2 `cd cli && uvx bump-my-version bump minor --config-file .bumpversion.toml --new-version 0.1.0` → produces commit + `cli-v0.1.0` tag
- [ ] 6.3 `git push --follow-tags`
- [ ] 6.4 Watch the Actions runs. Confirm `:v0.1.0`, `:0.1`, `:latest`, `:edge`, `:sha-…` tags appear at https://github.com/knowledge-circuit/knct-hub/pkgs/container/knct-hub
- [ ] 6.5 Confirm `@knct/cli@0.1.0` appears at https://www.npmjs.com/package/@knct/cli
- [ ] 6.6 If first npm publish claimed the scope under your user, transfer ownership to the `knct` org

## 7. Docs

- [ ] 7.1 Replace the README's Quick start with the three-command flow: `docker run …`, `npx @knct/cli init`, `open http://localhost:8765`
- [ ] 7.2 Create `docs/RELEASING.md` with both release procedures side by side (server: bump-my-version → push; CLI: bump-my-version → push), and the one-time `@knct` org transfer step
- [ ] 7.3 Note in `RELEASING.md` the SemVer 0.x convention (breaking changes can land in 0.X.0)

## 8. Smoke against the real registry

- [ ] 8.1 `docker pull ghcr.io/knowledge-circuit/knct-hub:v0.1.0` works on a clean machine (or `docker rmi` first to force a real pull)
- [ ] 8.2 `docker run --rm -p 8765:8765 ghcr.io/knowledge-circuit/knct-hub:v0.1.0` boots and `/api/v1/health` returns `{"ok": true}`
- [ ] 8.3 `npx @knct/cli@0.1.0 init --hub http://localhost:8765` in a scratch directory completes end-to-end
