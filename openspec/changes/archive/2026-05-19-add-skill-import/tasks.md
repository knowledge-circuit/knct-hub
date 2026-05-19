## 1. Dependency

- [x] 1.1 `cd dashboard && pnpm add yaml`

## 2. Parser

- [x] 2.1 Create `dashboard/src/lib/skill-import.ts` exporting `parseSkillMd(text: string)` returning a discriminated union `{ ok: true; skill: ParsedSkill } | { ok: false; error: string }`
- [x] 2.2 Split input on `^---\n([\\s\\S]*?)\n---\n?` to extract frontmatter and body; return error if the boundaries are missing
- [x] 2.3 `YAML.parse` the frontmatter block; catch and return parse errors as strings
- [x] 2.4 Validate `id` and `name` are non-empty strings after trimming; coerce `description` to string-or-null; coerce `keywords` to `string[]`, filter empty strings, dedupe preserving order
- [x] 2.5 Trim body and reject if empty

## 3. Drop area + button on the Skills page

- [x] 3.1 Add a visible drop area above the table with a dashed border, hint text ("Drop a .md file here, or click Import"), and dragover/dragleave styling
- [x] 3.2 Add an `Import` button next to "New skill" that programmatically clicks a hidden `<input type="file" accept=".md">`
- [x] 3.3 Wire both the button input and the drop area's `onDrop` handler to a shared `handleFile(file: File)` function
- [x] 3.4 Reject non-`.md` files at the drop area (check `file.name.endsWith(".md")`) with an inline error

## 4. Import preview dialog

- [x] 4.1 Create `dashboard/src/components/skill-import-dialog.tsx` rendering a controlled dialog with editable `id`, `name`, `description`, `keywords` (comma-separated input), and `body` (textarea) fields, prefilled from the parsed skill
- [x] 4.2 Disable the Save button while `id` or `name` is empty
- [x] 4.3 On Save, call the existing `api.upsertSkill(slug, id, {...})` and invalidate the skills query on success
- [x] 4.4 Render server-side errors (e.g. 4xx) inline within the dialog footer

## 5. Wire it up + smoke

- [x] 5.1 In `skills.tsx`, manage state for the parsed skill and dialog open flag; show parse errors inline in the drop area
- [x] 5.2 Smoke 1: drop `skills/commit-with-linear-refs.md` onto the drop area → preview opens with all fields populated → save → row appears in the table
- [x] 5.3 Smoke 2: import a file with malformed YAML → error in drop area, dialog does not open
- [x] 5.4 Smoke 3: import a file missing `id` → error in drop area
- [x] 5.5 Smoke 4: re-import the same file → silent upsert, no duplicate row

## 6. Docs

- [x] 6.1 Add a short note to `dashboard/README.md` (or main README) describing the import flow and the frontmatter shape
