import json

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import Kpatch, Trigger

VALID_EVENTS = ("session_start", "user_prompt", "pre_tool_use")


def serialize_trigger(t: Trigger) -> dict:
    return {
        "id": t.id,
        "kpatch_org_id": t.kpatch_org_id,
        "kpatch_id": t.kpatch_id,
        "event": t.event,
        "prompt_contains": (
            json.loads(t.prompt_contains) if t.prompt_contains else None
        ),
        "path_match": t.path_match,
        "once_per_session": t.once_per_session,
    }


def _default_once(event: str, payload_tool: str | None) -> bool:
    # Default true for pre_tool_use Reads, false otherwise (matches
    # rule-engine legacy semantics, now expressed per-trigger).
    return event == "pre_tool_use" and (payload_tool or "").lower() == "read"


async def _ensure_kpatch(
    session: AsyncSession, org_id: str, kpatch_id: str
) -> None:
    result = await session.exec(
        select(Kpatch).where(Kpatch.org_id == org_id, Kpatch.id == kpatch_id)
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="kpatch not found")


async def list_triggers(
    session: AsyncSession, org_id: str, kpatch_id: str
) -> list[dict]:
    await _ensure_kpatch(session, org_id, kpatch_id)
    result = await session.exec(
        select(Trigger)
        .where(
            Trigger.kpatch_org_id == org_id, Trigger.kpatch_id == kpatch_id
        )
        .order_by(Trigger.id)
    )
    return [serialize_trigger(t) for t in result.all()]


async def create_trigger(
    session: AsyncSession,
    org_id: str,
    kpatch_id: str,
    *,
    event: str,
    prompt_contains: list[str] | None,
    path_match: str | None,
    once_per_session: bool | None,
) -> dict:
    if event not in VALID_EVENTS:
        raise HTTPException(status_code=400, detail="invalid event")
    await _ensure_kpatch(session, org_id, kpatch_id)
    once = (
        once_per_session
        if once_per_session is not None
        else _default_once(event, None)
    )
    trigger = Trigger(
        kpatch_org_id=org_id,
        kpatch_id=kpatch_id,
        event=event,
        prompt_contains=(
            json.dumps(prompt_contains) if prompt_contains else None
        ),
        path_match=path_match,
        once_per_session=once,
    )
    session.add(trigger)
    await session.commit()
    await session.refresh(trigger)
    return serialize_trigger(trigger)


async def update_trigger(
    session: AsyncSession,
    org_id: str,
    kpatch_id: str,
    trigger_id: int,
    *,
    event: str,
    prompt_contains: list[str] | None,
    path_match: str | None,
    once_per_session: bool | None,
) -> dict:
    if event not in VALID_EVENTS:
        raise HTTPException(status_code=400, detail="invalid event")
    result = await session.exec(
        select(Trigger).where(
            Trigger.id == trigger_id,
            Trigger.kpatch_org_id == org_id,
            Trigger.kpatch_id == kpatch_id,
        )
    )
    trigger = result.first()
    if not trigger:
        raise HTTPException(status_code=404, detail="trigger not found")
    trigger.event = event
    trigger.prompt_contains = (
        json.dumps(prompt_contains) if prompt_contains else None
    )
    trigger.path_match = path_match
    trigger.once_per_session = (
        once_per_session
        if once_per_session is not None
        else _default_once(event, None)
    )
    await session.commit()
    await session.refresh(trigger)
    return serialize_trigger(trigger)


async def delete_trigger(
    session: AsyncSession, org_id: str, kpatch_id: str, trigger_id: int
) -> None:
    result = await session.exec(
        select(Trigger).where(
            Trigger.id == trigger_id,
            Trigger.kpatch_org_id == org_id,
            Trigger.kpatch_id == kpatch_id,
        )
    )
    trigger = result.first()
    if not trigger:
        raise HTTPException(status_code=404, detail="trigger not found")
    await session.delete(trigger)
    await session.commit()
