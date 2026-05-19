## ADDED Requirements

### Requirement: Kpatch markdown source format
The system SHALL accept kpatch source files in markdown-with-YAML-frontmatter format. A valid file SHALL begin with `---`, contain a YAML block, end the block with `---` on its own line, and provide the kpatch body as the markdown content after the closing `---`.

#### Scenario: Well-formed file accepted
- **GIVEN** a `.md` file beginning with `---`, a YAML block including `id` and `name`, a closing `---`, and markdown content below
- **WHEN** the file is parsed
- **THEN** the parser yields a kpatch record whose `id`, `name`, `description`, and `keywords` come from the frontmatter and whose `body` is the markdown below the closing `---`

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
- **WHEN** the file is imported under an org
- **THEN** the kpatch is upserted and exactly one trigger row is created referencing it with event `user_prompt` and `prompt_contains: ["commit"]`

#### Scenario: No default trigger creates no trigger
- **GIVEN** a file whose frontmatter omits `trigger`
- **WHEN** the file is imported
- **THEN** the kpatch is upserted and no trigger rows are created

### Requirement: Import endpoint and conflict behavior
The system SHALL expose `POST /api/v1/orgs/{org}/kpatches/import` accepting one markdown file body. On id collision the existing kpatch's body and metadata SHALL be silently upserted; existing triggers SHALL be preserved (not duplicated when the file's default trigger matches an existing one).

#### Scenario: Re-import preserves existing triggers
- **GIVEN** a kpatch already exists with two triggers
- **WHEN** the same file is re-imported with its default trigger
- **THEN** the body and metadata are upserted, no duplicate trigger is created, and the existing additional trigger is preserved

### Requirement: Dashboard import entry points
The dashboard SHALL provide two entry points on the Kpatches page: an **Import** button next to "New kpatch" that opens a file picker, and a visible drop area on the same page that accepts a dragged-and-dropped `.md` file.

#### Scenario: Button opens file picker
- **WHEN** the user clicks the Import button
- **THEN** a native file picker opens accepting `.md` files

#### Scenario: Drop area accepts dropped file
- **WHEN** the user drops a `.md` file onto the drop area
- **THEN** the file is uploaded to the import endpoint and a preview dialog opens
