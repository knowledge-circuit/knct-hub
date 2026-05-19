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
from knct_hub.services.evaluator import clear_dedupe, select_kpatches
from knct_hub.services.resolver import (
    EffectiveKpatch,
    resolve_effective_kpatches,
)

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


async def _process_event(
    session: AsyncSession,
    org: Org,
    project: Project,
    claude_event_name: str,
    internal_event: str,
    payload: dict,
) -> dict:
    effective = await resolve_effective_kpatches(session, org, project)
    if not effective:
        return {}
    selected: list[EffectiveKpatch] = await select_kpatches(
        session, effective, internal_event, payload
    )
    if not selected:
        return {}
    return inject_response(claude_event_name, _concat([k.body for k in selected]))


async def handle_session_start(
    session: AsyncSession, org: Org, project: Project, payload: dict
) -> dict:
    return await _process_event(
        session, org, project, "SessionStart", "session_start", payload
    )


async def handle_prompt_submit(
    session: AsyncSession, org: Org, project: Project, payload: dict
) -> dict:
    return await _process_event(
        session, org, project, "UserPromptSubmit", "user_prompt", payload
    )


async def handle_pre_tool(
    session: AsyncSession, org: Org, project: Project, payload: dict
) -> dict:
    tool = payload.get("tool_name") or (payload.get("tool_input") or {}).get(
        "tool_name"
    )
    if tool not in PRE_TOOL_USE_ALLOW:
        return {}
    return await _process_event(
        session, org, project, "PreToolUse", "pre_tool_use", payload
    )


async def handle_post_compact(
    session: AsyncSession, org: Org, project: Project, payload: dict
) -> dict:
    sid = payload.get("session_id")
    if sid:
        await clear_dedupe(session, sid)
    return {}
