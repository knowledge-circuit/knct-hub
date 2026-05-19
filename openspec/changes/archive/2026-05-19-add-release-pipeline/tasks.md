## 1. bump-my-version configs

- [x] 1.1 Create `server/.bumpversion.toml`: `current_version = "0.0.2"`, `tag_name = "v{new_version}"`, `commit = true`, `tag = true`, `allow_dirty = false`, `message = "chore: bump server to v{new_version}"`, file entry pointing at `server/pyproject.toml`'s `version = "..."` line
- [x] 1.2 Create `cli/.bumpversion.toml`: `current_version = "0.0.1"`, `tag_name = "cli-v{new_version}"`, file entry pointing at `cli/package.json`'s `"version": "..."` line
- [x] 1.3 Sanity: `cd server && uvx bump-my-version bump patch --dry-run --verbose` shows the expected diff without modifying files
- [x] 1.4 Same for the CLI config

## 2. CLI: migrate to pnpm

- [x] 2.1 `cd cli && rm package-lock.json && rm -rf node_modules`
- [x] 2.2 `cd cli && pnpm install` to generate `pnpm-lock.yaml`
- [x] 2.3 Confirm `pnpm run build` still produces a working `dist/cli.js`
- [x] 2.4 Update `cli/README.md` to use `pnpm install` / `pnpm run` instead of `npm install` / `npm run`

## 3. Dockerfile: OCI labels + pnpm for dashboard build

- [x] 3.1 Add OCI labels (source, description, licenses, revision, title, url, documentation) to the runtime stage; `revision` from `GIT_SHA` build-arg
- [x] 3.2 Migrate dashboard build stage from `npm ci` to `pnpm install --frozen-lockfile`; add `dashboard/.npmrc` and `packageManager` field to handle pnpm 11's stricter defaults
- [x] 3.3 Confirm `docker build .` still succeeds and `docker inspect` shows the labels

## 4. Image workflow

- [x] 4.1 Create `.github/workflows/image.yml` with triggers `push.branches: [main]` + `push.tags: [v*]` + `workflow_dispatch`
- [x] 4.2 Steps: `actions/checkout` → `docker/setup-qemu-action` → `docker/setup-buildx-action` → `docker/login-action` (ghcr.io with `github.actor` + `GITHUB_TOKEN`) → `docker/metadata-action` with the tag rules from the design doc → `docker/build-push-action` with `platforms: linux/amd64,linux/arm64`, `cache-from: type=gha`, `cache-to: type=gha,mode=max`, build-args for `revision`
- [x] 4.3 Set `permissions: { contents: read, packages: write }`
- [x] 4.4 Use `concurrency: { group: image-${{ github.ref }}, cancel-in-progress: true }` so rapid pushes don't queue up

## 5. CLI publish workflow

- [x] 5.1 Create `.github/workflows/cli.yml` with trigger `push.tags: [cli-v*]` + `workflow_dispatch`
- [x] 5.2 Steps: `actions/checkout` → `pnpm/action-setup` → `actions/setup-node@v4` (Node 22, `registry-url: https://registry.npmjs.org`, `cache: pnpm`, `cache-dependency-path: cli/pnpm-lock.yaml`) → `pnpm install --frozen-lockfile` (in `cli/`) → `pnpm run build` → `npm publish --provenance --access public` with `NODE_AUTH_TOKEN: secrets.NPM_TOKEN`
- [x] 5.3 Set `permissions: { contents: read, id-token: write }` (id-token is required for npm provenance)

## 6. Cut the first releases

- [x] 6.1 `cd server && uvx bump-my-version bump minor --new-version 0.1.0` → produces commit + `v0.1.0` tag
- [x] 6.2 `cd cli && uvx bump-my-version bump minor --new-version 0.1.0` → produces commit + `cli-v0.1.0` tag
- [x] 6.3 `git push --follow-tags` (first push didn't fire tag events; deleted + re-pushed tags as workaround)
- [x] 6.4 Image v0.1.0 published successfully at ghcr (tags `:v0.1.0`, `:0.1`, `:latest`, `:edge`, `:sha-…`)
- [x] 6.5 `@knct/cli@0.1.1` published (cli-v0.1.0 failed at npm 403/422; fixed package.json with repository/license/homepage/bugs, bumped to 0.1.1, second publish succeeded)
- [ ] 6.6 Transfer `@knct/cli` ownership to the `knct` npm org (manual one-time step; first publish may have claimed scope under personal user)

## 7. Docs

- [x] 7.1 Replace the README's Quick start with the three-command flow: `docker run …`, `npx @knct/cli init`, `open http://localhost:8765`
- [x] 7.2 Create `docs/RELEASING.md` with both release procedures side by side (server: bump-my-version → push; CLI: bump-my-version → push), and the one-time `@knct` org transfer step
- [x] 7.3 Note in `RELEASING.md` the SemVer 0.x convention (breaking changes can land in 0.X.0)

## 8. Smoke against the real registry

- [x] 8.1 `docker pull ghcr.io/knowledge-circuit/knct-hub:v0.1.0` works on a clean machine (verified by removing the local image and re-pulling)
- [x] 8.2 `docker run --rm -p 8765:8765 ghcr.io/knowledge-circuit/knct-hub:v0.1.0` boots and `/api/v1/health` returns `{"ok": true}`
- [x] 8.3 `pnpm dlx @knct/cli@0.1.1 init --hub http://localhost:8765` in a scratch directory completes end-to-end
