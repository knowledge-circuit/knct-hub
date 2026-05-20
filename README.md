# knct-hub

Smart context injection for AI coding agents. Scope-resolved, hook-driven, observable.

## Why knct-hub

- **AGENTS.md is dumb accumulation.** Everything in the path gets merged into context, which degrades agent performance as repos grow.
- **MCP is pull-based.** The model has to know to ask. Models forget or don't know what they don't know.
- **knct-hub is push-based via hooks.** Deterministic, scoped, observable. Kpatches are injected only when a matching trigger fires for the project/user.

## Concepts

- **kpatch** — a single markdown file (frontmatter + body) that gets injected into the agent's context when one of its **triggers** matches an event. The frontmatter optionally carries one default trigger; more can be added in the dashboard.
- **scope** — every kpatch lives at exactly one scope:
  - `org` — applies to every project in the org
  - `project` — applies to one project
  - `member` — applies to one user on one project
- **resolution** — for each hook, the server collects kpatches at all three scopes for `(caller_org, project, user)`, keeps the **lowest-scope** row per slug (member > project > org), and drops any with `disable=true`. The survivors' triggers are evaluated against the event.
- **override** = create a sibling kpatch at a lower scope with new content. **disable** = create the sibling with `disable=true`. No separate disable/override arrays.

## Supported agents

- **Claude Code** — supported. `npx @knct/cli init` wires the HTTP hooks in `.claude/settings.json`.
- **opencode** — planned, not started. The hub already speaks a clean JSON contract; the work is the plugin wrapper.

## Monorepo layout

```
knct-hub/
├── server/       # FastAPI hub server (Python). Run locally or deploy.
├── cli/          # @knct/cli — npx-installable CLI (TypeScript).
├── dashboard/    # React + Vite + Tailwind admin UI (bundled into the server image).
├── kpatches/     # this repo's own seed kpatches
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

## Authoring kpatches

A kpatch is a markdown file with a YAML frontmatter block. Create or import one from the dashboard's Kpatches page (org scope), the project kpatches view (project scope), or — once auth lands — the "My kpatches" view (member scope). Drop area + Import button both accept a `.md` file shaped like:

```markdown
---
id: commit-conventions             # required, kebab-case (the "slug")
name: Commit conventions           # required
description: One-liner...          # optional
keywords:                          # optional
  - commit
  - git commit
trigger:                           # optional default trigger
  event: user_prompt               # session_start | user_prompt | pre_tool_use
  prompt_contains: ["commit"]      # only for user_prompt
  path_match: "services/**"        # optional glob
---

# Body in markdown

The body below the closing `---` is the text that gets injected.
```

The file itself carries no scope hint — scope is determined by *where* you import it. The same file can be imported at multiple scopes, and lower-scope copies shadow higher-scope ones.

See [`kpatches/commit-with-linear-refs.md`](./kpatches/commit-with-linear-refs.md) for a real example.

## Inspect traces

```bash
curl 'http://localhost:8765/api/v1/traces?limit=10&only_injections=true'
sqlite3 ~/.knct/hub.db 'select ts, event, kpatch_ids from traces order by ts desc limit 20'
```

The dashboard's Traces page shows which kpatches fired for each hook (with chips, filters, and an "Only injections" toggle).

## Releases

Both server and CLI ship from GitHub Actions on tag push. See [`docs/RELEASING.md`](./docs/RELEASING.md) for the procedure.

## Status

Early. End-to-end working: scope-resolved kpatches (org / project / member) with override + disable via sibling rows, trigger engine with per-session dedupe, CLI initial wiring (`@knct/cli` on npm), dashboard with kpatch / trigger / project CRUD and a traces view bundled into the server image, automated multi-arch image to `ghcr.io`. Missing: auth (Clerk + device tokens in progress), community library, opencode plugin.
