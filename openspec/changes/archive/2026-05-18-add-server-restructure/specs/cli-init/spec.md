## MODIFIED Requirements

### Requirement: Existing project picker
The command SHALL fetch the hub's project list via `GET /api/v1/projects` and present an interactive picker offering a `<Create new>` option followed by every existing project's slug.

#### Scenario: User selects an existing project
- **WHEN** the picker is shown and the user selects an existing slug
- **THEN** no `POST /api/v1/projects` call is made and the selected slug is used in subsequent file writes

#### Scenario: User chooses to create a new project
- **WHEN** the user selects `<Create new>`
- **THEN** the command prompts for a slug, defaulting to the kebab-cased basename of the current working directory
- **AND** the command POSTs `/api/v1/projects` with the chosen slug
- **AND** uses the slug in subsequent file writes

#### Scenario: Hub unreachable
- **WHEN** `GET /api/v1/projects` fails to connect or returns a non-2xx status
- **THEN** the command exits with a non-zero status and a message indicating the hub could not be reached, suggesting `--hub` or starting the server locally

### Requirement: Claude Code settings generation
The command SHALL write `.claude/settings.json` at the repository root containing HTTP hook entries for `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, and `PostCompact`, each pointing at `<hub_url>/api/v1/hook` with an `X-Project-Slug: <slug>` header. If the file already exists, the command SHALL overwrite it without prompting.

#### Scenario: Settings file generated correctly
- **WHEN** the command completes
- **THEN** `.claude/settings.json` contains six hook event entries, each with `type: "http"`, the URL `<hub_url>/api/v1/hook`, and the `X-Project-Slug` header set to the resolved slug

#### Scenario: Existing settings overwritten
- **WHEN** `.claude/settings.json` exists with other hooks the user added
- **THEN** the file is overwritten with only the knct hook entries; pre-existing entries are lost
