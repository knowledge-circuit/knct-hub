# release-pipeline

## Purpose

Publish the server as a multi-arch Docker image to ghcr.io and the CLI as `@knct/cli` to npm, both driven by independent git tags and automated via GitHub Actions.

## Requirements

### Requirement: Server version bump produces a v-prefixed tag
The system SHALL provide a `bump-my-version` configuration at `server/.bumpversion.toml` that, when invoked, updates the version in `server/pyproject.toml`, creates a git commit, and creates an annotated git tag of the form `v{X.Y.Z}`.

#### Scenario: Minor bump on server
- **GIVEN** the current server version is `0.1.0`
- **WHEN** the user runs `cd server && uvx bump-my-version bump minor`
- **THEN** `server/pyproject.toml`'s `version` line reads `0.2.0`
- **AND** a commit and tag `v0.2.0` exist on the current branch

### Requirement: CLI version bump produces a cli-v-prefixed tag
The system SHALL provide a separate `bump-my-version` configuration at `cli/.bumpversion.toml` that updates the version in `cli/package.json`, commits, and creates a tag of the form `cli-v{X.Y.Z}`.

#### Scenario: Patch bump on CLI
- **GIVEN** the current CLI version is `0.1.0`
- **WHEN** the user runs `cd cli && uvx bump-my-version bump patch`
- **THEN** `cli/package.json`'s `version` field reads `0.1.1`
- **AND** a commit and tag `cli-v0.1.1` exist

### Requirement: Image published to ghcr on main + v* tag
A GitHub Actions workflow SHALL build and push the Docker image at `ghcr.io/knowledge-circuit/knct-hub` for both `linux/amd64` and `linux/arm64` architectures, on every push to `main` and on every tag matching `v*`. The workflow SHALL use the built-in `GITHUB_TOKEN` and SHALL NOT require a separately-managed PAT.

#### Scenario: Push to main publishes edge tag
- **WHEN** a commit is pushed to `main`
- **THEN** the workflow builds the image and pushes it to ghcr with tags `:edge` and `:sha-<short>` (where `<short>` is the first 7 characters of the commit SHA)

#### Scenario: Version tag publishes pinned + latest
- **WHEN** a tag `v0.2.0` is pushed
- **THEN** the workflow builds the image and pushes it with tags `:v0.2.0`, `:0.2`, and `:latest`

### Requirement: CLI published to npm on cli-v* tag
A GitHub Actions workflow SHALL publish `@knct/cli` to npm on every tag matching `cli-v*`. The workflow SHALL install dependencies with `pnpm install --frozen-lockfile`, build the package, and run `npm publish --provenance --access public` using the `NPM_TOKEN` repository secret.

#### Scenario: CLI tag triggers publish
- **WHEN** a tag `cli-v0.2.0` is pushed
- **THEN** the workflow builds the CLI and publishes `@knct/cli@0.2.0` to npm with provenance and public access

#### Scenario: Image workflow does not fire on cli tag
- **WHEN** a tag `cli-v0.2.0` is pushed
- **THEN** the image workflow does not run for this tag

### Requirement: CLI uses pnpm
The CLI package SHALL use pnpm as its package manager. The repository SHALL contain `cli/pnpm-lock.yaml` and SHALL NOT contain `cli/package-lock.json`.

#### Scenario: Lockfile present
- **WHEN** a contributor clones the repository
- **THEN** `cli/pnpm-lock.yaml` exists and `cli/package-lock.json` does not

### Requirement: Dockerfile carries OCI labels
The built image SHALL include OCI metadata labels at minimum: `org.opencontainers.image.source`, `org.opencontainers.image.description`, `org.opencontainers.image.licenses`, `org.opencontainers.image.revision`.

#### Scenario: Labels readable via docker inspect
- **WHEN** a user runs `docker inspect ghcr.io/knowledge-circuit/knct-hub:latest`
- **THEN** the output contains the four OCI labels with non-empty values
