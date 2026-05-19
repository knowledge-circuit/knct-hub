"""Shape hook responses to Claude Code's injection protocol.

For events that support context injection, returns
``{"hookSpecificOutput": {"hookEventName": <event>, "additionalContext":
<markdown>}}``. When no kpatches fire the response is ``{}``.

Track A wires SessionStart, UserPromptSubmit, and PreToolUse through the
new resolver + evaluator pipeline. PostCompact clears the per-session
trigger dedupe state.
"""

from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import Org, Project
from typing import NamedTuple

from knct_hub.services.evaluator import clear_dedupe, select_kpatches
from knct_hub.services.resolver import resolve_effective_kpatches


class HookOutcome(NamedTuple):
    response: dict
    kpatch_ids: list[str]
    trigger_ids: list[int]

# PreToolUse is processed only for these tools (per context-injection spec).
PRE_TOOL_USE_ALLOW = ("Edit", "Write", "Read")

# Map Claude Code hook event names to internal kpatch trigger events.
EVENT_NAME_MAP = {
    "SessionStart": "session_start",
    "UserPromptSubmit": "user_prompt",
    "PreToolUse": "pre_tool_use",
}


def inject_response(claude_event_name: str, markdown: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": claude_event_name,
            "additionalContext": markdown,
        }
    }


def _concat(bodies: list[str]) -> str:
    return "\n\n---\n\n".join(bodies)


_EMPTY = HookOutcome({}, [], [])


async def _process_event(
    session: AsyncSession,
    org: Org,
    project: Project,
    claude_event_name: str,
    internal_event: str,
    payload: dict,
) -> HookOutcome:
    effective = await resolve_effective_kpatches(session, org, project)
    if not effective:
        return _EMPTY
    selected = await select_kpatches(session, effective, internal_event, payload)
    if not selected:
        return _EMPTY
    kpatch_ids = [k.id for k, _ in selected]
    trigger_ids = [tid for _, tids in selected for tid in tids]
    body = _concat([k.body for k, _ in selected])
    return HookOutcome(
        inject_response(claude_event_name, body), kpatch_ids, trigger_ids
    )


async def handle_session_start(
    session: AsyncSession, org: Org, project: Project, payload: dict
) -> HookOutcome:
    return await _process_event(
        session, org, project, "SessionStart", "session_start", payload
    )


async def handle_prompt_submit(
    session: AsyncSession, org: Org, project: Project, payload: dict
) -> HookOutcome:
    return await _process_event(
        session, org, project, "UserPromptSubmit", "user_prompt", payload
    )


async def handle_pre_tool(
    session: AsyncSession, org: Org, project: Project, payload: dict
) -> HookOutcome:
    tool = payload.get("tool_name") or (payload.get("tool_input") or {}).get(
        "tool_name"
    )
    if tool not in PRE_TOOL_USE_ALLOW:
        return _EMPTY
    return await _process_event(
        session, org, project, "PreToolUse", "pre_tool_use", payload
    )


async def handle_post_compact(
    session: AsyncSession, org: Org, project: Project, payload: dict
) -> HookOutcome:
    sid = payload.get("session_id")
    if sid:
        await clear_dedupe(session, sid)
    return _EMPTY
