---
id: commit-with-linear-refs
name: Commit with Linear project refs
description: Compose git commits for this repo with the right type prefix, Linear KC-NNN ref derived from the branch name, and the project's hard rules (no --no-verify, no amend, no Co-Authored-By, one Refs per branch).
triggers: [commit, committing, committed, "git commit"]
---

# Commit with Linear project refs

Project-local overlay for committing in this repo. Apply *in addition to*
Claude Code's generic commit guidance.

## Gather context first (run in parallel)

```bash
git status
git diff                              # both staged and unstaged
git log --oneline -10
git log main..HEAD --oneline          # if non-empty, you're on a branch
git rev-parse --abbrev-ref HEAD       # current branch name
```

## Branch → Linear ID

Branch format: `<user>/kc-<NNN>-<slug>`
  example: `maro/kc-243-add-github-topics-to-knct-hub-repo`

Extract `KC-<NNN>` from the branch with regex `kc-(\d+)` (case-insensitive).
The full ID is `KC-<NNN>`.

Optional enrichment: fetch the ticket title via `gh issue view` or the
Linear MCP if available. Use it for the commit body when it sharpens the
"why."

## Message format

```
<type>: <imperative lowercase subject, ≤72 chars, no period>

[optional body, wrap ~72 chars; explain WHY when not obvious]

[Refs KC-NNN]
```

### Allowed types
- **feat** — new user-facing capability
- **fix** — bug fix; describe what broke, not just the area
- **chore** — tooling, deps, CI, docs, refactors with no behavior change
- **spec** — OpenSpec changes. Sub-verbs: `spec: add <change>`,
  `spec: archive <change>`, `spec: sync <change>`

No other types (no `docs:`, no `refactor:`, no `style:`).

### Refs trailer rules

- Exactly **one** commit per branch carries `Refs KC-NNN`.
- Put it on the **first** commit of the branch.
- Before committing, run `git log main..HEAD` — if a commit on this branch
  already carries a Refs trailer, this commit must omit it.
- On `main` (no branch): omit Refs.

## Hard rules

- Never `--no-verify`, never `--no-gpg-sign`.
- Never amend a published commit; create a new one.
- Never add a `Co-Authored-By` trailer.
- Use HEREDOC for multiline `git commit -m` to preserve newlines.
- Always ask the user to confirm the drafted message before committing.

## Example (correct shape)

```
feat: bundle dashboard into server and add docker setup

Serve the built dashboard at / with SPA fallback for client
routes, add GET /api/v1/health, and a KNCT_DASHBOARD_DIST env
var resolving to dashboard/dist by default.

Refs KC-241
```
