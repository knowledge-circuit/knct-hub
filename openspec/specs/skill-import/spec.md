# skill-import

## Purpose

Import a single skill into the hub from a markdown file with YAML frontmatter, with strict parsing, a preview dialog for review, and silent upsert on conflict. Defined as a capability so a future CLI or server-side endpoint can implement the same contract.

## Requirements

### Requirement: Skill markdown source format
The system SHALL accept skill source files in markdown-with-YAML-frontmatter format. A valid file SHALL begin with `---`, contain a YAML block, end the block with `---` on its own line, and provide the skill body as the markdown content after the closing `---`.

#### Scenario: Well-formed file accepted
- **GIVEN** a `.md` file beginning with `---`, a YAML block including `id` and `name`, a closing `---`, and markdown content below
- **WHEN** the file is parsed
- **THEN** the parser yields a skill record whose `id`, `name`, `description`, and `keywords` come from the frontmatter and whose `body` is the markdown below the closing `---`

#### Scenario: File without frontmatter rejected
- **WHEN** a file is parsed that does not begin with `---` or has no closing `---`
- **THEN** the parser returns an error describing the missing frontmatter; no skill record is produced

### Requirement: Required and optional frontmatter fields
The parser SHALL require non-empty `id` and `name` in the frontmatter. It SHALL accept `description` as an optional string and `keywords` as an optional list of strings. Empty keyword strings and duplicates SHALL be removed.

#### Scenario: Missing required field rejected
- **WHEN** a file's frontmatter omits `id` or `name`, or either field is empty after trimming
- **THEN** the parser returns an error naming the missing field(s); no skill record is produced

#### Scenario: Keywords normalized
- **GIVEN** a `keywords` list `["a", "", "b", "a"]`
- **WHEN** the file is parsed
- **THEN** the resulting `keywords` field is `["a", "b"]`

### Requirement: Import entry points in the dashboard
The Skills page SHALL provide two entry points to import a skill from a file: an **Import** button next to "New skill" that opens a file picker, and a visible drop area on the same page that accepts a dragged-and-dropped `.md` file.

#### Scenario: Button opens file picker
- **WHEN** the user clicks the Import button
- **THEN** a native file picker opens accepting `.md` files

#### Scenario: Drop area accepts dropped file
- **WHEN** the user drags a `.md` file onto the drop area and releases it
- **THEN** the same import flow runs as the button-triggered flow

#### Scenario: Non-md file rejected at the drop area
- **WHEN** the user drops a file whose extension is not `.md`
- **THEN** the drop area surfaces an inline error and the import flow does not run

### Requirement: Preview dialog with editable parsed fields
On successful parse, the system SHALL open a dialog populated with the parsed `id`, `name`, `description`, `keywords` (comma-separated), and `body`. All fields SHALL be editable. The dialog SHALL include a Save action that performs an upsert via the existing skill upsert endpoint and a Cancel action that discards the import.

#### Scenario: Save commits the import
- **GIVEN** the preview dialog is open with parsed fields
- **WHEN** the user clicks Save
- **THEN** the dashboard issues `PUT /api/v1/projects/{slug}/skills/{id}` with the dialog's current field values
- **AND** on success the skills list refreshes and the dialog closes

#### Scenario: Cancel discards the import
- **WHEN** the user clicks Cancel or closes the dialog without saving
- **THEN** no request is made and the skills list is unchanged

#### Scenario: Inline errors during edit
- **WHEN** the user clears the `id` or `name` field in the preview dialog
- **THEN** the Save button is disabled until both fields are non-empty

### Requirement: Silent upsert on conflict
The system SHALL upsert the imported skill against `PUT /api/v1/projects/{slug}/skills/{id}` without prompting the user about whether a skill with the same `id` already exists.

#### Scenario: Existing skill replaced silently
- **GIVEN** a skill with `id` "commit-with-linear-refs" already exists in the current project
- **WHEN** the user imports a file with the same `id` and saves the preview dialog
- **THEN** the server returns HTTP 200 and the skills list shows the updated record without an additional confirmation step

### Requirement: Inline parse-error feedback
When parsing fails, the system SHALL display the parser's error message in the drop area and SHALL NOT open the preview dialog.

#### Scenario: Malformed YAML
- **WHEN** the user imports a file whose frontmatter contains invalid YAML
- **THEN** the drop area shows the YAML parser's error message
- **AND** the preview dialog does not open
