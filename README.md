# knct-hub

Smart context injection for AI coding agents. Per-project, hook-driven, observable.

## Why knct-hub

- **AGENTS.md is dumb accumulation.** Everything in the path gets merged into context, which degrades agent performance as repos grow.
- **MCP is pull-based.** The model has to know to ask. Models forget or don't know what they don't know.
- **knct-hub is push-based via hooks.** Deterministic, scoped, observable. Skills are injected only when the rules match.

## Supported agents

- **Claude Code** — supported. `npx @knct/cli init` wires the HTTP hooks in `.claude/settings.json`.
- **opencode** — planned, not started. The hub already speaks a clean JSON contract; the work is the plugin wrapper.

## Monorepo layout

```
knct-hub/
├── server/       # FastAPI hub server (Python).  Run locally or deploy.
├── cli/          # @knct/cli — npx-installable CLI (TypeScript).
├── dashboard/    # React + Vite + Tailwind admin UI (WIP, dev-mode only).
├── .knct/        # this repo's own knct config (we dogfood)
└── .claude/      # this repo's own Claude Code hook wiring
```

See [`server/`](./server), [`cli/`](./cli), and [`dashboard/`](./dashboard) for component-level docs.

## Quick start

### Docker (recommended for dogfooding)

```bash
docker compose up -d               # builds the image, runs in the background
open http://localhost:8765         # UI + API on the same port
```

The container restarts automatically (`restart: unless-stopped`) and persists data to `./data/hub.db` on the host.

### From source

Run the hub:

```bash
cd server
uv run python -m knct_hub          # listens on http://127.0.0.1:8765
```

All endpoints live under `/api/v1/...`. Database lives at `~/.knct/hub.db` (SQLite by default; Postgres supported via `KNCT_DATABASE_URL`).

Run the dashboard separately during development:

```bash
cd dashboard
npm install
npm run dev                        # http://localhost:5173, proxies /api → :8765
```

### Wire a repo up

In any repo you want to wire up:

```bash
npx @knct/cli init
```

This writes `.knct/config.toml` and `.claude/settings.json`. Restart Claude Code to pick up the hooks.

## Authoring skills

Skills can be created in the dashboard's New-skill dialog, or imported from a markdown file with YAML frontmatter. The dashboard's Skills page has an **Import** button and a drop area that accept a `.md` file shaped like:

```markdown
---
id: my-skill                  # required, kebab-case
name: My skill                # required
description: One-liner...     # optional
keywords:                     # optional
  - one
  - another
---

# Skill body in markdown

The body below the closing `---` becomes the skill's `body`.
```

See [`skills/commit-with-linear-refs.md`](./skills/commit-with-linear-refs.md) for a real example.

## Inspect traces

```bash
curl 'http://localhost:8765/api/v1/traces?limit=10'
sqlite3 ~/.knct/hub.db 'select ts, event, tool_name from traces order by ts desc limit 20'
```

Or open the dashboard's traces page.

## Status

Early. What works end-to-end: injection engine (skills, rules, dedupe), CLI initial wiring, and a dashboard with projects/skills/rules/traces CRUD bundled into the server when run via Docker. What's missing: auth, no published `@knct/cli` on npm, no opencode plugin.
