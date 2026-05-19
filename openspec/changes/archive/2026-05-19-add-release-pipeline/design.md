## Context

We've got a runnable Docker image, a usable CLI, and a working dashboard — all reachable only by cloning the repo and running build commands manually. The next step toward letting anyone else dogfood is a release pipeline that publishes the image to a registry and the CLI to npm, on a predictable cadence driven by git tags.

The product has two independently-evolving components — the server image and the CLI — and we want their versions to reflect their actual change cadence, not be coupled artificially. The release pipeline must support bumping each on its own.

## Goals / Non-Goals

**Goals:**
- One-command bump for the server (`uvx bump-my-version bump <part>` in `server/`) that updates `pyproject.toml`, commits, and tags `vX.Y.Z`.
- Same shape for the CLI in `cli/`, with tag prefix `cli-vX.Y.Z`.
- A `git push --follow-tags` after either bump triggers the correct CI workflow and produces a published artifact.
- Multi-arch image (linux/amd64 + linux/arm64) so M-series Macs and x86 servers both pull native binaries.
- npm publish runs with `--provenance` so attestation is recorded against the GitHub Actions run that produced the artifact.
- A user who's never cloned the repo can install everything in three commands.

**Non-Goals:**
- Conventional-commit-driven version bumping (release-please, semantic-release). We pick the part manually because the change cadence and audience don't justify the automation.
- Coupled / unified versions across server and CLI.
- Image signing (cosign / sigstore). Provenance via npm's free attestation is enough for v1; image signing is a separate change if/when we want it.
- Custom GitHub release notes generation. Tag push is enough; users read commit log.
- Pre-release / alpha channels on either ghcr or npm. We ship from `main`.
- Publishing the dashboard as a separate package. It only ships bundled into the server image.
- Releasing the *dashboard* on a separate cadence. It rides along with the server image.

## Decisions

**Two independent `bump-my-version` configs.** One in `server/` (tag `v{new}`), one in `cli/` (tag `cli-v{new}`). Both run via `uvx`, no install required. Considered: single root config bumping both files at once — rejected because the CLI's change cadence is much lower than the server's, and we'd publish identical-content npm versions on every server-only change.

**Tag conventions: `v0.1.0` and `cli-v0.1.0`.** Different prefixes give each CI workflow a clean filter. `v*` (server) and `cli-v*` (CLI). Considered: scoping the server's tags to `server-v*` for symmetry — rejected because the bare `v*` is the conventional "this is the project" tag and the server is the project's center of gravity; the CLI is the addon.

**Image tags emitted by CI:**
- On push to `main`: `:edge`, `:sha-<short>` — moving + immutable
- On `v*` tag: `:vX.Y.Z`, `:X.Y`, `:latest`
- Use `docker/metadata-action` to compute them uniformly

Considered: only tagging on releases (no `edge`) — rejected, the moving tag is genuinely useful for dogfooders who want to track main. Considered: omitting `:latest` — rejected, users expect it for "give me the newest stable."

**Multi-arch via `docker/setup-qemu-action` + buildx.** `linux/amd64` and `linux/arm64`. Cache via `cache-from/to=gha` keeps build times reasonable across the two platforms. Considered: amd64-only — rejected; M-series Macs are common and emulation under x86-only images is slow + unreliable.

**npm publish with `--provenance --access public`.** Provenance is one flag and gives users a verifiable link from the npm package to the GitHub workflow run that produced it. `--access public` is required for scoped packages on a free npm plan. Considered: skipping provenance — rejected, costs nothing.

**`NPM_TOKEN` is a granular token scoped to the `@knct` org.** Provided by the user as a repo secret. The workflow does NOT log into npm; `setup-node` writes the registry URL into `.npmrc` and `npm publish` reads `NODE_AUTH_TOKEN` from env.

**`GITHUB_TOKEN` for ghcr.** Built-in, no PAT needed. Workflow needs `permissions: packages: write`. Considered: a personal access token — rejected, more setup, no benefit.

**Dockerfile gains OCI labels.** ghcr surfaces them on the package page and tooling like Renovate uses them. Standard set: `source`, `description`, `licenses`, `revision`. `revision` comes from a build arg the workflow passes (`--build-arg GIT_SHA=…`). Considered: skipping labels — rejected, two-line ergonomic win.

**CLI moves to pnpm.** Workspace is mixed (dashboard already pnpm). Removing the holdout keeps the toolchain consistent and the package-manager memory ([feedback memory](file://~/.claude/projects/-Users-maro-Projects-marodevs-knct-hub/memory/feedback_pnpm.md)) honest. CI workflow uses `pnpm install --frozen-lockfile`. Considered: leaving cli/ on npm — rejected, drift that costs more in friction than the migration costs.

**Initial release is `v0.1.0` for both.** Versions today are `0.0.2` (server) and `0.0.1` (cli). Bumping to `0.1.0` marks "this is real enough for someone else to use." Considered: starting from `0.0.3` / `0.0.2` — rejected, "0.1" reads better as the first published version and the project has earned it.

**Release procedure is documented in `docs/RELEASING.md`.** A short page with both flows side by side. Considered: putting it in the README — rejected, releasing is an ops procedure, not part of the user-facing pitch.

## Risks / Trade-offs

- **Two configs means two release commands.** A small UX tax; explicitly chosen over false bumps on the CLI side.
- **Multi-arch builds cost CI minutes.** ~3 min per arch on cold cache, ~30 sec each warm. Mitigated by `cache-from/to=gha`.
- **First publish creates the `@knct` scope on npm.** The first `npm publish` claims the scope under the publishing user's account; the user must then transfer ownership to the `knct` org. Manual one-time step, documented in `RELEASING.md`.
- **No image signing in v1.** If supply-chain integrity matters more later, add cosign. Today the audience is small enough that provenance via npm + immutable digests on ghcr are enough.
- **Push to `main` triggers `:edge` rebuild every commit.** Cheap with cache; if it becomes annoying, add a path filter (skip when only `openspec/` or `docs/` changed).
- **CI workflow runs for changes that don't actually affect the artifact.** Same mitigation as above (path filters) if it bites.

## Migration / Cutover

1. Land this change's code (workflows, bumpversion configs, Dockerfile labels, pnpm-migrate CLI, docs).
2. Verify the image workflow runs green on the `main` push that lands this change → expect `:edge` and `:sha-<short>` tags to appear in the ghcr package page.
3. From a clean working tree, bump and tag the server: `uvx bump-my-version bump minor --config-file server/.bumpversion.toml` (0.0.2 → 0.1.0), then `git push --follow-tags`. Confirm `:v0.1.0`, `:0.1`, `:latest` appear in ghcr.
4. Same for CLI: `uvx bump-my-version bump minor --config-file cli/.bumpversion.toml` (0.0.1 → 0.1.0), then `git push --follow-tags`. Confirm the workflow runs and `@knct/cli@0.1.0` appears on npm.
5. Update `compose.yml` if needed to pin to `:v0.1.0` rather than `:latest` for stability.

## Open Questions

- **Should the image workflow also publish on PRs?** Today it runs on `push` only. PR builds (ephemeral, untagged) would surface build breakage earlier. Could add later as a follow-up; not load-bearing for v1.
- **Is `0.1.0` a SemVer 0.x signal that breaking changes can land in 0.2.0?** Yes by convention. Document it in `RELEASING.md`.
- **Do we want a CHANGELOG?** Probably yes eventually. Skipping for v1 to keep this change focused.
