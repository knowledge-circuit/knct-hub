# session-map

## Purpose

On `SessionStart`, push a lightweight "map" of available skills and rule counts to the agent — an index, not full content.

## Requirements

### Requirement: SessionStart returns a project map
On `SessionStart`, the system SHALL respond with a markdown summary of the project's available skills and rule count, returned via `hookSpecificOutput.additionalContext`. The map SHALL list each skill's name and one-line description but SHALL NOT include skill bodies.

#### Scenario: Map content shape
- **WHEN** a `SessionStart` event arrives for a project with 3 skills and 4 rules
- **THEN** the response's `additionalContext` contains a header line summarizing the counts and a bulleted list of `name: description` lines, one per skill

#### Scenario: Empty project still responds
- **WHEN** a `SessionStart` event arrives for a project with no skills and no rules
- **THEN** the response is `{}` (no injection)
