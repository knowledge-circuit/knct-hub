# Releasing

The repo ships two artifacts on independent cadences:

| Artifact | Tag prefix | Registry |
|----------|------------|----------|
| Server image | `v*` | `ghcr.io/knowledge-circuit/knct-hub` |
| CLI npm package | `cli-v*` | `@knct/cli` on npmjs.com |

Both releases use [`bump-my-version`](https://github.com/callowayproject/bump-my-version) via `uvx` and are picked up by GitHub Actions on tag push.

## Server release

```bash
cd server

# bump the patch / minor / major component
uvx bump-my-version bump <patch|minor|major>

# pushes the commit + tag
git push --follow-tags
```

This triggers [`.github/workflows/image.yml`](../.github/workflows/image.yml), which:

- Builds the multi-arch image (`linux/amd64` + `linux/arm64`)
- Pushes to `ghcr.io/knowledge-circuit/knct-hub` with tags `:vX.Y.Z`, `:X.Y`, and `:latest`
- Always-pushed tags from `main`: `:edge`, `:sha-<short>`

To force a specific version (e.g. for the first release):

```bash
uvx bump-my-version bump --new-version 0.1.0
```

## CLI release

```bash
cd cli

uvx bump-my-version bump <patch|minor|major>

git push --follow-tags
```

This triggers [`.github/workflows/cli.yml`](../.github/workflows/cli.yml), which:

- Installs deps with `pnpm install --frozen-lockfile`
- Runs `pnpm run build`
- `npm publish --provenance --access public` with the `NPM_TOKEN` secret

### First publish — claim the `@knct` scope

The very first `npm publish` of `@knct/cli` will fail unless the `@knct` org or scope exists. Set this up once:

1. Create the `knct` org at https://www.npmjs.com/org/create
2. After the first successful publish, confirm the package shows the `knct` org as owner (not your personal user)
3. If it landed under your user, transfer ownership: https://www.npmjs.com/package/@knct/cli/access

## Versioning convention

Semantic versioning on both components. While we're on `0.x`:

- **`0.X.0`** (minor bump) — breaking changes allowed
- **`0.X.Y`** (patch bump) — bug fixes, doc tweaks, no behavior break

Once we cut `1.0.0`, breaking changes only land on a major bump.

## What to do if a release fails

1. **Build failure in CI** — fix the cause, commit the fix, run `bump-my-version` again (it'll bump from the failed version forward — that's fine, no one ever pulled the broken one)
2. **`bump-my-version` refuses on dirty tree** — commit or stash your unrelated changes first, then re-run
3. **Wrong tag pushed** — `git tag -d <tag> && git push --delete origin <tag>`, then run `bump-my-version` again

Don't `git tag -f` over an existing tag once anyone has consumed the artifact (npm registry doesn't allow overwriting versions; ghcr will but immutability is the point).
