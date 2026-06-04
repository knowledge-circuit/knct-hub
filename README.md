# knct-hub

Smart context injection for AI coding agents. Local-first, hook-driven, observable.

## Why

- **AGENTS.md is dumb accumulation.** Everything in the path gets merged into context, which degrades agent performance as repos grow.
- **MCP is pull-based.** The model has to know to ask. Models forget or don't know what they don't know.
- **kpatches are push-based via hooks.** Deterministic, scoped to a prompt, observable. Only the kpatches whose triggers match a given prompt are folded into context.

## Concepts

- **kpatch** — a single markdown file (`.knct/kpatches/<id>.md`) with frontmatter + body. When one of its **triggers** matches the user prompt, the body is folded into context. Use `always: true` for unconditional injection.
- **hook** — `.knct/hooks/inject.py` runs on every `UserPromptSubmit`, walks `.knct/kpatches/`, matches triggers against the prompt, and emits the matching bodies as `additionalContext` for Claude Code.
- **statusline** — `.knct/bin/statusline.sh` reads the most recent injection state (written by the hook into `.knct/state/`) and shows which kpatches fired on the last prompt.

## Supported agents

- **Claude Code** — supported. `npx @knct/cli init` writes the hook, statusline, and starter kpatches into your repo.
- **opencode** — planned. The hook contract is plain JSON on stdin/stdout; the work is the plugin wrapper.

## Quick start

```bash
cd path/to/your/repo
npx @knct/cli init
```

Pick a project slug and check the starter kpatches you want. Restart Claude Code so the new hooks load. That's it — no server, no network, no Docker.

See [`cli/README.md`](./cli/README.md) for the full command reference.

## Monorepo layout

```
knct-hub/
├── cli/              # @knct/cli — npx-installable CLI (TypeScript). The supported install path.
├── cli/assets/       # inject.py + statusline.sh (canonical, bundled into the CLI).
├── cli/kpatches/     # starter kpatch library bundled into the CLI.
├── .knct/            # this repo dogfoods knct — its own hook, statusline, and kpatches.
├── .claude/          # this repo's Claude Code hook wiring.
├── server/           # PAUSED: FastAPI hub server (kept for reference, see server/README.md).
└── dashboard/        # PAUSED: React admin UI for the server.
```

## Authoring kpatches

A kpatch is a markdown file with YAML frontmatter:

```markdown
---
id: commit-conventions             # required, kebab-case
name: Commit conventions           # required
description: One-liner...          # shown in `knct kpatch add` picker
triggers: [commit, "git commit"]   # case-insensitive substring match on the prompt
---

# Body in markdown

The body below the closing `---` is the text that gets folded into context
whenever a trigger matches.
```

Use `always: true` instead of `triggers:` to inject on every prompt.

See [`cli/kpatches/commit-with-linear-refs.md`](./cli/kpatches/commit-with-linear-refs.md) for a real example.

## Releases

The CLI ships from GitHub Actions on tag push. See [`docs/RELEASING.md`](./docs/RELEASING.md).

## Status

Local-first kpatch flow works end-to-end: bundled hook + statusline + starter library installed via `@knct/cli init`, idempotent settings.json merge, `knct upgrade` for refreshing assets, `knct kpatch add` for picking more from the library. The server and dashboard (org/project/member scope resolution, traces UI, project CRUD) are paused; the path forward there depends on real demand for team-wide kpatch sharing.
