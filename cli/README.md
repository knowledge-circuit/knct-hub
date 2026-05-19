# @knct/cli

CLI for [knct-hub](../). Links a repository to a hub project so Claude Code's hooks know where to send events.

The CLI talks to the hub under `/api/v1/...` and writes hook URLs that point at `<hub>/api/v1/hook`.

## Usage

```bash
npx @knct/cli init
```

Runs interactively: prompts for a hub URL, fetches the project list, and lets you pick an existing project or create a new one. Writes:

- `.knct/config.toml` — slug + hub URL (overwritten if present)
- `.claude/settings.json` — hook entries for the six wired events, each with an `X-Project-Slug` header (overwritten if present)

After init, **restart Claude Code** so the new hook settings are picked up.

### Options

| Flag | Description |
|------|-------------|
| `--hub <url>` | Hub URL. Skips the URL prompt. Default if prompted: `http://localhost:8765`. |
| `-h, --help` | Show usage. |

### Examples

Solo / local hub:
```bash
npx @knct/cli init --hub http://localhost:8765
```

Team / remote hub:
```bash
npx @knct/cli init --hub https://hub.your-team.dev
```

## Development

```bash
pnpm install
pnpm run dev -- init --hub http://localhost:8765   # iterate via tsx
pnpm run build                                     # bundle to dist/cli.js
node dist/cli.js init                             # run the built bundle
```

### Running locally as `knct`

To use `knct` as a real command on your PATH before the package is published:

```bash
cd cli
pnpm link --global    # symlinks `knct` globally
knct init             # runs from any directory
# undo with:
pnpm unlink --global @knct/cli
```

The hub must be running first (`cd ../server && uv run python -m knct_hub`).

## Release

Releases are automated. Bump the version with `bump-my-version`, push the tag, and GitHub Actions publishes:

```bash
cd cli
uvx bump-my-version bump <patch|minor|major>   # commits + tags cli-vX.Y.Z
git push --follow-tags                          # triggers .github/workflows/cli.yml
```

See [`docs/RELEASING.md`](../docs/RELEASING.md) for the full procedure.
