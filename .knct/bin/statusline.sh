#!/bin/sh
# kpatch v0 statusline. Reads .knct/state/<session_id>.json (written by
# inject.py on each UserPromptSubmit) and emits a compact line listing
# the kpatches injected on the last prompt. Empty output on error or none.

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null)
[ -n "$session_id" ] || exit 0

proj="${CLAUDE_PROJECT_DIR:-}"
[ -n "$proj" ] || proj=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)
[ -n "$proj" ] || proj="$PWD"

state_file="$proj/.knct/state/$session_id.json"
[ -f "$state_file" ] || exit 0

names=$(jq -r '(.kpatches // []) | join(", ")' "$state_file" 2>/dev/null)
[ -n "$names" ] && printf 'kpatch: %s' "$names"
exit 0
