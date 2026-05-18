# @knct/cli

CLI for [knct-hub](../). Links a repository to a hub project so Claude Code's hooks know where to send events.

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
npm install
npm run dev -- init --hub http://localhost:8765   # iterate via tsx
npm run build                                     # bundle to dist/cli.js
node dist/cli.js init                             # run the built bundle
```

### Running locally as `knct`

To use `knct` as a real command on your PATH before the package is published:

```bash
cd cli
npm link              # symlinks `knct` globally
knct init             # runs from any directory
# undo with:
npm unlink -g @knct/cli
```

The hub must be running first (`cd ../server && uv run python -m knct_hub`).

## Publish (manual, not yet wired)

```bash
npm run build
npm run pack:dry          # sanity check the tarball contents
# npm publish --access public
```
