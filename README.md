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

```bash
# 1. Run the hub (image is published to ghcr; no clone needed):
docker run -d --name knct-hub \
  --restart unless-stopped \
  -p 8765:8765 -v ~/.knct:/data \
  ghcr.io/knowledge-circuit/knct-hub:latest

# 2. Wire any repo you want to dogfood:
npx @knct/cli init

# 3. Open the dashboard + API on the same port:
open http://localhost:8765
```

The container restarts automatically and persists data to `~/.knct/hub.db` on the host. All endpoints live under `/api/v1/...`. SQLite by default; Postgres supported via `KNCT_DATABASE_URL`.

### From source

If you want to hack on the code rather than run the published image:

```bash
# server
cd server
uv run python -m knct_hub          # listens on http://127.0.0.1:8765

# dashboard (separate dev server, proxies /api → :8765)
cd dashboard
pnpm install
pnpm run dev                       # http://localhost:5173

# or build everything into one image
docker compose up -d --build
```

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

## Releases

Both server and CLI ship from GitHub Actions on tag push. See [`docs/RELEASING.md`](./docs/RELEASING.md) for the procedure.

## Status

Early. What works end-to-end: injection engine (skills, rules, dedupe), CLI initial wiring (published as `@knct/cli` on npm), dashboard with projects/skills/rules/traces CRUD bundled into the server image, automated multi-arch image to `ghcr.io`. What's missing: auth, no opencode plugin.
