## Context

Skills currently can only be authored through individual form fields in the dashboard's New/Edit dialog. The `skills/` directory in this repo already has a markdown-with-frontmatter source format (see `skills/commit-with-linear-refs.md`). The natural authoring workflow is: write the markdown locally, then import into the hub. The dashboard is the right home for that import in v1 — it's where users already manage skills.

## Goals / Non-Goals

**Goals:**
- One-click import from a `.md` file with YAML frontmatter.
- Two entry points on the Skills page: a button (file picker) and a visible drop area.
- A preview dialog with editable parsed fields, so users can adjust before saving.
- Strict validation: clear inline errors for malformed input.
- Silent upsert: if the file's `id` matches an existing skill, replace it without confirmation.

**Non-Goals:**
- Multi-file or directory import.
- Server-side import endpoint (`POST /skills/import`).
- CLI `knct skill import` subcommand.
- A markdown editor with live preview in the import dialog — plain textarea is enough for v1.
- Round-trip export (writing skills back to `.md` files) — separate change.
- Diffing against the existing record before upsert — silent upsert per user direction.
- Authoring rules through the same import flow — only skills for now.

## Decisions

**`yaml` package, not `js-yaml` and not hand-rolled.** Modern, ~10 kB, well-maintained, handles every edge case our hand-roll would miss (quoted strings, escapes, multi-line values). `js-yaml` is bigger (~30 kB) for no extra benefit. Hand-rolling would break on the first description containing a colon.

**Frontmatter shape: required `id`, `name`; optional `description`, `keywords`.** Mirrors the existing `SkillBody` Pydantic model. `body` comes from the markdown after the closing `---`. Required fields are non-empty after trimming.

**Preview dialog reuses the existing Skill edit dialog shape.** Same fields, same validation feedback, same Save button. The only difference is that fields come pre-filled from the parsed file instead of empty. This keeps the UI surface minimal and behavior consistent.

**Silent upsert via the existing PUT endpoint.** No new server route. The user has already seen and edited the fields in the preview dialog, so the save click is informed consent. No "skill already exists, overwrite?" prompt.

**Drop area visible above the table; same handler as the file picker.** Two affordances, one code path: both produce a `File`, both go through `parseSkillMd`, both open the preview dialog. Drop area shows a hint message ("Drop a `.md` file here, or click Import"), highlights on dragover, accepts only `.md` files.

**Parser lives in `src/lib/skill-import.ts`.** Pure function: `parseSkillMd(text: string): ParsedSkill | ParseError`. Returns a discriminated union, never throws — callers render errors inline.

**Validation is one place.** The parser validates structure (frontmatter present, YAML parses) AND content (required fields non-empty). One pass, one error message, no double-validation in the dialog.

**Errors surface inline in the drop-area zone, not via toast.** Toast doesn't exist in the dashboard yet and adding one is scope creep. Drop area already has space for an error message.

## Risks / Trade-offs

- **YAML parsing is permissive** → a malformed file could parse but produce a nonsense skill. Mitigated by the preview dialog: the user sees what was parsed before saving.
- **Silent upsert may overwrite work** → user explicitly asked for this; the preview dialog gives them a chance to back out (close = no save).
- **Frontmatter format diverges from the server's API shape** → low risk; both are stable and small. If the API gains fields, update the parser to pass them through.
- **No round-trip export** → users can't re-edit a hub skill as a file without recreating it. Acceptable for v1; revisit if it becomes a workflow gap.
- **Big files** → parser reads the entire file into memory. Skill bodies are small (KB-range markdown); no practical concern.
- **CORS** → all import happens client-side; no cross-origin concerns.

## Open Questions

- **Should we strip a leading `# <title>` from the body if it duplicates `name`?** Probably not — users can decide; we don't need to be clever. Document the convention in the help text instead.
- **What happens if `keywords` contains duplicates or empty strings?** Parser trims and deduplicates. Empty strings filtered out.
- **Should the drop area also accept paste-text?** Out of scope for v1; the button + drop cover the common cases.
