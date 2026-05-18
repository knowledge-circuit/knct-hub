import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from knct_hub.db.models import Trace
from knct_hub.db.session import get_session
from knct_hub.services.injection import (
    handle_post_compact,
    handle_pre_tool,
    handle_prompt_submit,
    handle_session_start,
)
from knct_hub.services.projects import ensure_project

router = APIRouter()


def _slug_from(request: Request) -> str:
    slug = request.headers.get("x-project-slug")
    if not slug:
        raise HTTPException(status_code=400, detail="missing X-Project-Slug header")
    return slug


async def _insert_trace(
    session: AsyncSession, payload: dict, response: dict
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
    )
    session.add(trace)
    await session.commit()


@router.post("/hook")
async def hook(
    request: Request, session: AsyncSession = Depends(get_session)
) -> dict:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid JSON")
    if not isinstance(payload, dict):
        payload = {"_raw": payload}

    slug = _slug_from(request)
    await ensure_project(session, slug)

    event = payload.get("hook_event_name")
    if event == "SessionStart":
        resp = await handle_session_start(session, slug, payload)
    elif event == "UserPromptSubmit":
        resp = await handle_prompt_submit(session, slug, payload)
    elif event == "PreToolUse":
        resp = await handle_pre_tool(session, slug, payload)
    elif event == "PostCompact":
        resp = await handle_post_compact(session, slug, payload)
    else:
        resp = {}

    await _insert_trace(session, payload, resp)
    return resp


@router.get("/traces")
async def traces(
    limit: int = 100, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    limit = max(1, min(limit, 1000))
    result = await session.exec(
        select(Trace).order_by(Trace.ts.desc()).limit(limit)
    )
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
        }
        out.append(row)
    return out
