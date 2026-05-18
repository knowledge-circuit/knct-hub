# context-injection

## Purpose

Shape hook responses to Claude Code's injection protocol so matched skills are pushed into agent context.

## Requirements

### Requirement: Hook response uses Claude Code injection protocol
For events that support context injection (`SessionStart`, `UserPromptSubmit`, `PreToolUse`), the system SHALL return a JSON body of the form `{"hookSpecificOutput": {"hookEventName": "<event>", "additionalContext": "<markdown>"}}` when one or more rules fire. When no rules fire the server SHALL return `{}`.

#### Scenario: Rules fire produce additionalContext
- **WHEN** a `PreToolUse:Edit` event matches one or more rules
- **THEN** the response body contains `hookSpecificOutput.additionalContext` set to the concatenated markdown of the matched skills' `body` fields

#### Scenario: No rules fire return empty
- **WHEN** no rule matches the event
- **THEN** the response body is `{}`

### Requirement: PreToolUse tool filtering
The system SHALL only process `PreToolUse` events for tools `Edit`, `Write`, and `Read`. Other tools SHALL receive `{}` regardless of rule configuration.

#### Scenario: PreToolUse for Bash ignored
- **WHEN** a `PreToolUse` event arrives with `tool_input.tool_name: "Bash"`
- **THEN** the response is `{}` and no rule evaluation runs

### Requirement: Response logged
The system SHALL record the response body in the `traces.response` column alongside the existing request payload row.

#### Scenario: Injection visible in traces
- **WHEN** a hook is processed and rules fire
- **THEN** `GET /traces` shows the row with both the original `payload` and the `response` that was returned
