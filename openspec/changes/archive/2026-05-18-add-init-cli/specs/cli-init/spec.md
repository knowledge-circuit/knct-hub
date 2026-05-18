## ADDED Requirements

### Requirement: knct init command exists
The system SHALL provide a `knct init` command, distributed via the `@knct/cli` npm package, that can be invoked with `npx @knct/cli init` and writes the two files required to link the current working directory to a hub project.

#### Scenario: Command runs in an empty directory
- **WHEN** a user runs `knct init` in a directory that contains no `.knct/` or `.claude/`
- **THEN** the command completes successfully and creates `.knct/config.toml` and `.claude/settings.json`

### Requirement: Hub URL resolution
The command SHALL resolve the hub URL in this priority: explicit `--hub <url>` flag, else an interactive prompt with `http://localhost:8765` as the default.

#### Scenario: Flag wins over prompt
- **WHEN** the user runs `knct init --hub https://hub.team.dev`
- **THEN** no prompt for hub URL is shown and the value `https://hub.team.dev` is used

#### Scenario: Prompt used when flag absent
- **WHEN** the user runs `knct init` with no `--hub` flag in an interactive terminal
- **THEN** the user is prompted for a hub URL with `http://localhost:8765` as the default

### Requirement: Existing project picker
The command SHALL fetch the hub's project list via `GET /projects` and present an interactive picker offering a `<Create new>` option followed by every existing project's slug.

#### Scenario: User selects an existing project
- **WHEN** the picker is shown and the user selects an existing slug
- **THEN** no `POST /projects` call is made and the selected slug is used in subsequent file writes

#### Scenario: User chooses to create a new project
- **WHEN** the user selects `<Create new>`
- **THEN** the command prompts for a slug, defaulting to the kebab-cased basename of the current working directory
- **AND** the command POSTs `/projects` with the chosen slug
- **AND** uses the slug in subsequent file writes

#### Scenario: Hub unreachable
- **WHEN** `GET /projects` fails to connect or returns a non-2xx status
- **THEN** the command exits with a non-zero status and a message indicating the hub could not be reached, suggesting `--hub` or starting the server locally

### Requirement: Config file generation
The command SHALL write `.knct/config.toml` at the repository root containing `slug` and `hub_url`. If the file already exists, the command SHALL overwrite it without prompting.

#### Scenario: New config written
- **WHEN** the command runs successfully and `.knct/config.toml` does not exist
- **THEN** the file is created with the resolved slug and hub URL

#### Scenario: Existing config overwritten
- **WHEN** the command runs successfully and `.knct/config.toml` already exists
- **THEN** the file is overwritten with the new slug and hub URL without prompting

### Requirement: Claude Code settings generation
The command SHALL write `.claude/settings.json` at the repository root containing HTTP hook entries for `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, and `PostCompact`, each pointing at `<hub_url>/hook` with an `X-Project-Slug: <slug>` header. If the file already exists, the command SHALL overwrite it without prompting.

#### Scenario: Settings file generated correctly
- **WHEN** the command completes
- **THEN** `.claude/settings.json` contains six hook event entries, each with `type: "http"`, the resolved hub URL, and the `X-Project-Slug` header set to the resolved slug

#### Scenario: Existing settings overwritten
- **WHEN** `.claude/settings.json` exists with other hooks the user added
- **THEN** the file is overwritten with only the knct hook entries; pre-existing entries are lost

### Requirement: Completion summary
On success, the command SHALL print a short summary listing the linked project, the hub URL, the files written, and a reminder to restart Claude Code.

#### Scenario: Success message includes the essentials
- **WHEN** `knct init` completes successfully
- **THEN** the output names the slug, the hub URL, the two file paths that were written, and instructs the user to restart Claude Code
