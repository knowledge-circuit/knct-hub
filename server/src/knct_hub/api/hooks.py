import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import Trace
from knct_hub.db.session import get_session
from knct_hub.services.auth import Caller, resolve_caller
from knct_hub.services.injection import (
    handle_post_compact,
    handle_pre_tool,
    handle_prompt_submit,
    handle_session_start,
)
from knct_hub.services.orgs import get_org
from knct_hub.services.projects import authorize_hook, ensure_project

router = APIRouter()


def _slug_from(request: Request) -> str:
    slug = request.headers.get("x-project-slug")
    if not slug:
        raise HTTPException(status_code=400, detail="missing X-Project-Slug header")
    return slug


async def _insert_trace(
    session: AsyncSession,
    payload: dict,
    response: dict,
    *,
    org_id: str | None = None,
    project_slug: str | None = None,
    kpatch_ids: list[str] | None = None,
    trigger_ids: list[int] | None = None,
) -> None:
    tool_input = payload.get("tool_input") or {}
    trace = Trace(
        ts=datetime.now(timezone.utc),
        event=payload.get("hook_event_name") or "<unknown>",
        session_id=payload.get("session_id"),
        cwd=payload.get("cwd"),
        tool_name=payload.get("tool_name") or tool_input.get("tool_name"),
        payload=json.dumps(payload),
        response=json.dumps(response),
        kpatch_ids=json.dumps(kpatch_ids) if kpatch_ids else None,
        triggered_by=json.dumps(trigger_ids) if trigger_ids else None,
        project_org_id=org_id,
        project_slug=project_slug,
    )
    session.add(trace)
    await session.commit()


@router.post("/hook")
async def hook(
    request: Request,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid JSON")
    if not isinstance(payload, dict):
        payload = {"_raw": payload}

    slug = _slug_from(request)
    org = await get_org(session, caller.active_org_id)
    project = await ensure_project(session, org.id, slug)
    project = await authorize_hook(session, project, caller.user_id)

    event = payload.get("hook_event_name")
    if event == "SessionStart":
        outcome = await handle_session_start(session, project, caller.user_id, payload)
    elif event == "UserPromptSubmit":
        outcome = await handle_prompt_submit(session, project, caller.user_id, payload)
    elif event == "PreToolUse":
        outcome = await handle_pre_tool(session, project, caller.user_id, payload)
    elif event == "PostCompact":
        outcome = await handle_post_compact(session, project, caller.user_id, payload)
    else:
        from knct_hub.services.injection import HookOutcome

        outcome = HookOutcome({}, [], [])

    await _insert_trace(
        session,
        payload,
        outcome.response,
        org_id=org.id,
        project_slug=project.slug,
        kpatch_ids=outcome.kpatch_ids,
        trigger_ids=outcome.trigger_ids,
    )
    return outcome.response


@router.get("/traces")
async def traces(
    limit: int = 100,
    only_injections: bool = False,
    org_id: str | None = None,
    project_slug: str | None = None,
    event: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    limit = max(1, min(limit, 1000))
    q = select(Trace).order_by(Trace.ts.desc())
    if only_injections:
        q = q.where(Trace.kpatch_ids.is_not(None))
    if org_id:
        q = q.where(Trace.project_org_id == org_id)
    if project_slug:
        q = q.where(Trace.project_slug == project_slug)
    if event:
        q = q.where(Trace.event == event)
    q = q.limit(limit)
    result = await session.exec(q)
    out: list[dict] = []
    for t in result.all():
        row = {
            "id": t.id,
            "ts": t.ts.isoformat() if t.ts else None,
            "event": t.event,
            "session_id": t.session_id,
            "cwd": t.cwd,
            "tool_name": t.tool_name,
            "payload": json.loads(t.payload) if t.payload else None,
            "response": json.loads(t.response) if t.response else None,
            "kpatch_ids": json.loads(t.kpatch_ids) if t.kpatch_ids else [],
            "triggered_by": json.loads(t.triggered_by) if t.triggered_by else [],
            "project_org_id": t.project_org_id,
            "project_slug": t.project_slug,
        }
        out.append(row)
    return out
