## Why

The hub and the CLI run end-to-end on a developer machine, but nobody else can install either of them. To dogfood with anyone other than the author — and to let `npx @knct/cli init` actually work — we need automated release pipelines: a Docker image published to ghcr.io and `@knct/cli` published to npm, both driven by git tags. We also need a disciplined way to bump versions in the right files so tags, package metadata, and image labels stay in sync.

## What Changes

- Add **two independent `bump-my-version` configs**: one at `server/.bumpversion.toml` (tag prefix `v`), one at `cli/.bumpversion.toml` (tag prefix `cli-v`). The server and CLI version independently.
- Add `.github/workflows/image.yml`: builds the multi-arch Docker image on every push to `main` (tags `:edge`, `:sha-<short>`) and on every `v*` tag (tags `:vX.Y.Z`, `:X.Y`, `:latest`), pushes to `ghcr.io/knowledge-circuit/knct-hub`.
- Add `.github/workflows/cli.yml`: on `cli-v*` tag, installs CLI deps with pnpm, builds, and runs `npm publish --provenance --access public`. Uses the repo's `NPM_TOKEN` secret.
- Migrate `cli/` to **pnpm**: delete `package-lock.json`, generate `pnpm-lock.yaml`, update CI workflow + Dockerfile (the dashboard already uses pnpm; `cli/` is the holdout).
- Add **OCI labels** to the Dockerfile so the published image carries `org.opencontainers.image.source`, `description`, `licenses`, `revision`, etc.
- Update the README to lead with a three-command install — `docker run … ghcr.io/...:latest`, `npx @knct/cli init`, open the UI — rather than the clone-first quick start.
- Add a `docs/RELEASING.md` page documenting both release procedures (`bump-my-version` + `git push --follow-tags` for each component).
- Cut initial **v0.1.0** releases of both server and CLI as part of applying this change (manual `bump-my-version` invocation, tag push, verify CI).

## Capabilities

### New Capabilities
- `release-pipeline`: CI-driven publication of the Docker image to ghcr.io and the `@knct/cli` package to npm, triggered by version tags. Defines tag conventions, image tagging policy, and publish provenance.

### Modified Capabilities
<!-- None — server and CLI behavior are unchanged at runtime. -->

## Impact

- New CI workflows under `.github/workflows/`. The image workflow runs on every push to `main` and on `v*` tags; the CLI workflow runs only on `cli-v*` tags.
- New GitHub Actions secret used: `NPM_TOKEN` (already configured by the user). No PAT needed for ghcr — `GITHUB_TOKEN` has `packages: write` scope.
- Dockerfile gains OCI label lines but the build process is unchanged.
- `cli/package-lock.json` is replaced by `cli/pnpm-lock.yaml`. Existing `npm install` in CLI README docs updated to `pnpm install`.
- Image becomes pullable from `ghcr.io/knowledge-circuit/knct-hub:latest` and tagged versions; pre-existing local `compose.yml` already references this image name.
- `@knct/cli` becomes publicly installable via `npm i @knct/cli` / `npx @knct/cli`. The `@knct` org/scope is created implicitly on first publish.
- No runtime behavior change for any existing endpoint or page.
