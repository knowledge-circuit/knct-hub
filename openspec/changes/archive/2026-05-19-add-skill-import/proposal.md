## Why

Authoring skills through individual form fields in the dashboard is friction-heavy and doesn't compose with how dev knowledge actually lives: in markdown files in a repo, in a shared doc, or as snippets people pass around. A markdown-with-frontmatter source format makes skills portable, reviewable, and easy to seed in bulk. Importing one of those files into the hub should be a single click in the dashboard.

## What Changes

- Add an "Import" button next to "New skill" on the dashboard's Skills page.
- Support **single-file import** via two entry points: a hidden file picker triggered by the button, and a drop area visible on the same page.
- Parse a markdown file with YAML frontmatter into a skill record. Required frontmatter keys: `id`, `name`. Optional: `description`, `keywords` (list of strings). The body below the closing `---` becomes the skill's `body`.
- Show a **preview dialog** with the parsed fields rendered into editable inputs (id, name, description, keywords as comma-separated text, body as textarea) so the user can adjust before saving.
- On save, **silently upsert** via `PUT /api/v1/projects/{slug}/skills/{id}` — same path as existing edit/create.
- Validate the parsed file: reject if frontmatter is missing, malformed, or any required field is empty; show the error inline in the import area.

## Capabilities

### New Capabilities
- `skill-import`: markdown-with-frontmatter parsing, validation rules, and the preview-before-save flow. Currently realized by the dashboard, but the capability is named so a future CLI or server-side endpoint can implement it consistently.

### Modified Capabilities
<!-- None — server endpoints unchanged. -->

## Impact

- New dashboard dependency: `yaml` (~10 kB) for frontmatter parsing.
- New files: `dashboard/src/lib/skill-import.ts` (parser + validator), `dashboard/src/components/skill-import-dialog.tsx` (preview modal). Existing `dashboard/src/pages/skills.tsx` gains the button, dropzone, and dialog wiring.
- No server changes. Existing `PUT /api/v1/projects/{slug}/skills/{id}` does the upsert.
- No CLI changes. (Follow-up `knct skill import` is possible later; out of scope here.)
- No new auth or security surface — runs entirely in the user's browser against their own hub.
