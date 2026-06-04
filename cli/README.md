# @knct/cli

Local-first kpatch installer for [Claude Code](https://docs.claude.com/en/docs/claude-code).

A **kpatch** is a markdown file with frontmatter. The hook installed by this CLI
reads `.knct/kpatches/*.md` on every `UserPromptSubmit`, picks the ones whose
triggers match the prompt, and folds their bodies into context. The companion
statusline shows which kpatches fired last.

No server, no network. Everything lives in the repo.

## Usage

```bash
npx @knct/cli init
```

Interactive. Prompts for a project slug and a multi-select of starter kpatches,
then writes:

- `.knct/config.toml` — just the slug for now
- `.knct/hooks/inject.py` — UserPromptSubmit hook (Python, stdlib only)
- `.knct/bin/statusline.sh` — statusline reading the latest injection state
- `.knct/kpatches/*.md` — the kpatches you picked
- `.claude/settings.json` — merged: adds the inject hook + statusline, preserves
  any other entries you already had

Restart Claude Code after init so the new hooks load.

## Commands

| Command | What it does |
|---|---|
| `knct init` | First-time setup. Idempotent — safe to re-run. |
| `knct upgrade` | Re-emit `inject.py` and `statusline.sh` from the bundled assets. Run after `npm i -g @knct/cli@latest`. |
| `knct kpatch add` | Pick more from the bundled library and copy them in. Won't overwrite existing files. |

## Writing your own kpatch

Drop a markdown file in `.knct/kpatches/`:

```markdown
---
id: my-rule
name: My rule
description: One-liner for the picker.
triggers: [keyword, "another phrase"]
---

# Body

This text is folded into context whenever the prompt contains one of the
triggers (case-insensitive substring match). Use `always: true` instead of
`triggers:` to inject on every prompt.
```

## Development

```bash
pnpm install
pnpm run dev -- init                    # iterate via tsx
pnpm run build                          # bundle + inline assets into dist/cli.js
node dist/cli.js init                   # run the built bundle
```

The bundle inlines `assets/inject.py`, `assets/statusline.sh`, and every
`kpatches/*.md` as strings via esbuild's text loader, so the published npm
package is just `dist/cli.js`.

`assets/inject.py` and `assets/statusline.sh` are the canonical copies — edit
them here, then `pnpm run build` and either republish or `knct upgrade` in
consumer repos.

### Running locally as `knct`

```bash
cd cli
pnpm install && pnpm run build
pnpm install -g .       # registers `knct` globally; pnpm 10 syntax
knct init
# undo with:
pnpm uninstall -g @knct/cli
```

> Don't use `pnpm link --global .` — pnpm 10 writes a self-referencing
> `"@knct/cli": "link:"` into this package.json, which then breaks future
> `pnpm install` runs.

## Release

```bash
cd cli
uvx bump-my-version bump <patch|minor|major>   # commits + tags cli-vX.Y.Z
git push --follow-tags                          # triggers .github/workflows/cli.yml
```

See [`docs/RELEASING.md`](../docs/RELEASING.md) for the full procedure.
