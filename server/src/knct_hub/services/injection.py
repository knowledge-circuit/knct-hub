"""Shape hook responses to Claude Code's injection protocol.

Returns ``{"hookSpecificOutput": {"hookEventName": <event>,
"additionalContext": <markdown>}}`` when one or more kpatches fire,
``{}`` otherwise. PostCompact clears the per-session trigger dedupe.
"""


from typing import NamedTuple

from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import Project
from knct_hub.services.evaluator import clear_dedupe, select_kpatches
from knct_hub.services.resolver import resolve_effective_kpatches


class HookOutcome(NamedTuple):
    response: dict
    kpatch_ids: list[str]
    trigger_ids: list[int]


_EMPTY = HookOutcome({}, [], [])

PRE_TOOL_USE_ALLOW = ("Edit", "Write", "Read")


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
    project: Project,
    user_id: str,
    claude_event_name: str,
    internal_event: str,
    payload: dict,
) -> HookOutcome:
    effective = await resolve_effective_kpatches(
        session,
        org_id=project.org_id,
        project_slug=project.slug,
        user_id=user_id,
    )
    if not effective:
        return _EMPTY
    selected = await select_kpatches(session, effective, internal_event, payload)
    if not selected:
        return _EMPTY
    kpatch_ids = [k.slug for k, _ in selected]
    trigger_ids = [tid for _, tids in selected for tid in tids]
    body = _concat([k.body for k, _ in selected if k.body])
    if not body:
        return HookOutcome({}, kpatch_ids, trigger_ids)
    return HookOutcome(
        inject_response(claude_event_name, body), kpatch_ids, trigger_ids
    )


async def handle_session_start(
    session: AsyncSession, project: Project, user_id: str, payload: dict
) -> HookOutcome:
    return await _process_event(
        session, project, user_id, "SessionStart", "session_start", payload
    )


async def handle_prompt_submit(
    session: AsyncSession, project: Project, user_id: str, payload: dict
) -> HookOutcome:
    return await _process_event(
        session, project, user_id, "UserPromptSubmit", "user_prompt", payload
    )


async def handle_pre_tool(
    session: AsyncSession, project: Project, user_id: str, payload: dict
) -> HookOutcome:
    tool = payload.get("tool_name") or (payload.get("tool_input") or {}).get("tool_name")
    if tool not in PRE_TOOL_USE_ALLOW:
        return _EMPTY
    return await _process_event(
        session, project, user_id, "PreToolUse", "pre_tool_use", payload
    )


async def handle_post_compact(
    session: AsyncSession, project: Project, user_id: str, payload: dict
) -> HookOutcome:
    sid = payload.get("session_id")
    if sid:
        await clear_dedupe(session, sid)
    return _EMPTY
