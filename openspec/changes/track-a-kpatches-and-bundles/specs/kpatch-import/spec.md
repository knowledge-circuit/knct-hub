## ADDED Requirements

### Requirement: Kpatch markdown source format
The system SHALL accept kpatch source files in markdown-with-YAML-frontmatter format. A valid file SHALL begin with `---`, contain a YAML block, end the block with `---` on its own line, and provide the kpatch body as the markdown content after the closing `---`.

#### Scenario: Well-formed file accepted
- **GIVEN** a `.md` file beginning with `---`, a YAML block including `id` and `name`, a closing `---`, and markdown content below
- **WHEN** the file is parsed
- **THEN** the parser yields a kpatch record whose `slug`, `name`, `description`, and `keywords` come from the frontmatter and whose `body` is the markdown below the closing `---`

#### Scenario: File without frontmatter rejected
- **WHEN** a file is parsed that does not begin with `---` or has no closing `---`
- **THEN** the parser returns an error describing the missing frontmatter and no record is produced

### Requirement: Required and optional frontmatter fields
The parser SHALL require non-empty `id` and `name` in the frontmatter. It SHALL accept `description` as an optional string and `keywords` as an optional list of strings. Empty keyword strings and duplicates SHALL be removed.

#### Scenario: Missing required field rejected
- **WHEN** a file's frontmatter omits `id` or `name`, or either field is empty after trimming
- **THEN** the parser returns an error naming the missing field(s)

#### Scenario: Keywords normalized
- **GIVEN** a `keywords` list `["a", "", "b", "a"]`
- **WHEN** the file is parsed
- **THEN** the resulting `keywords` field is `["a", "b"]`

### Requirement: Optional default trigger block
The parser SHALL accept an optional `trigger` block in the frontmatter with fields `event` (one of `session_start`, `user_prompt`, `pre_tool_use`), optional `prompt_contains` (array of strings), and optional `path_match` (glob string). When present, the importer SHALL create exactly one trigger row tied to the imported kpatch.

#### Scenario: Default trigger creates one trigger row
- **GIVEN** a file whose frontmatter contains `trigger: { event: user_prompt, prompt_contains: ["commit"] }`
- **WHEN** the file is imported at a scope
- **THEN** the kpatch is upserted at that scope and exactly one trigger row is created referencing it via the kpatch's surrogate `pk_id`

#### Scenario: No default trigger creates no trigger
- **GIVEN** a file whose frontmatter omits `trigger`
- **WHEN** the file is imported
- **THEN** the kpatch is upserted and no trigger rows are created

### Requirement: Scope is selected at import time
The system SHALL expose import endpoints at every scope and SHALL place the resulting kpatch at the scope identified by the chosen endpoint. The markdown file itself SHALL NOT carry a scope hint; scope is determined by where it is imported. The endpoints are:

- `POST /api/v1/orgs/{org}/kpatches/import` — org scope
- `POST /api/v1/orgs/{org}/projects/{slug}/kpatches/import` — project scope
- `POST /api/v1/orgs/{org}/projects/{slug}/members/{user_id}/kpatches/import` — member scope

#### Scenario: Project-scope import lands at project scope
- **WHEN** a file is POSTed to `/api/v1/orgs/acme/projects/web/kpatches/import`
- **THEN** the resulting kpatch row has `scope="project"`, `org_id="acme"`, `project_slug="web"`

### Requirement: Import conflict behavior
On slug collision *at the same scope tuple*, the existing kpatch's body and metadata SHALL be silently upserted; existing triggers SHALL be preserved (no duplicate created when the file's default trigger matches an existing one).

#### Scenario: Re-import preserves existing triggers at same scope
- **GIVEN** a kpatch already exists at org scope with two triggers
- **WHEN** the same file is re-imported at the same scope with its default trigger
- **THEN** the body and metadata are upserted, no duplicate trigger is created, and the existing additional trigger is preserved

### Requirement: Dashboard import entry points
The dashboard SHALL provide import entry points on each scope-specific kpatch list view: an **Import** button next to "New kpatch" that opens a file picker, and a visible drop area on the same page that accepts a dragged-and-dropped `.md` file. The chosen scope is implicit in the view the user is on.

#### Scenario: Button opens file picker
- **WHEN** the user clicks the Import button on any scope's kpatch list
- **THEN** a native file picker opens accepting `.md` files

#### Scenario: Drop area accepts dropped file
- **WHEN** the user drops a `.md` file onto the drop area
- **THEN** the file is uploaded to the import endpoint for the current scope and a preview dialog opens
