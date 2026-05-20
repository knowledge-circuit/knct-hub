"""Trigger CRUD. Triggers FK by integer kpatch_id (the surrogate pk_id)."""


import json

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import Kpatch, Trigger

VALID_EVENTS = ("session_start", "user_prompt", "pre_tool_use")


def serialize_trigger(t: Trigger) -> dict:
    return {
        "id": t.id,
        "kpatch_id": t.kpatch_id,
        "event": t.event,
        "prompt_contains": (
            json.loads(t.prompt_contains) if t.prompt_contains else None
        ),
        "path_match": t.path_match,
        "once_per_session": t.once_per_session,
    }


async def _ensure_kpatch(session: AsyncSession, kpatch_pk_id: int) -> Kpatch:
    result = await session.exec(
        select(Kpatch).where(Kpatch.pk_id == kpatch_pk_id)
    )
    k = result.first()
    if not k:
        raise HTTPException(status_code=404, detail="kpatch not found")
    return k


async def list_triggers(
    session: AsyncSession, kpatch_pk_id: int
) -> list[dict]:
    await _ensure_kpatch(session, kpatch_pk_id)
    result = await session.exec(
        select(Trigger)
        .where(Trigger.kpatch_id == kpatch_pk_id)
        .order_by(Trigger.id)
    )
    return [serialize_trigger(t) for t in result.all()]


async def create_trigger(
    session: AsyncSession,
    kpatch_pk_id: int,
    *,
    event: str,
    prompt_contains: list[str] | None,
    path_match: str | None,
    once_per_session: bool | None,
) -> dict:
    if event not in VALID_EVENTS:
        raise HTTPException(status_code=400, detail="invalid event")
    await _ensure_kpatch(session, kpatch_pk_id)
    once = (
        once_per_session if once_per_session is not None else False
    )
    trigger = Trigger(
        kpatch_id=kpatch_pk_id,
        event=event,
        prompt_contains=json.dumps(prompt_contains) if prompt_contains else None,
        path_match=path_match,
        once_per_session=once,
    )
    session.add(trigger)
    await session.commit()
    await session.refresh(trigger)
    return serialize_trigger(trigger)


async def update_trigger(
    session: AsyncSession,
    kpatch_pk_id: int,
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
            Trigger.id == trigger_id, Trigger.kpatch_id == kpatch_pk_id
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
        once_per_session if once_per_session is not None else False
    )
    await session.commit()
    await session.refresh(trigger)
    return serialize_trigger(trigger)


async def delete_trigger(
    session: AsyncSession, kpatch_pk_id: int, trigger_id: int
) -> None:
    result = await session.exec(
        select(Trigger).where(
            Trigger.id == trigger_id, Trigger.kpatch_id == kpatch_pk_id
        )
    )
    trigger = result.first()
    if not trigger:
        raise HTTPException(status_code=404, detail="trigger not found")
    await session.delete(trigger)
    await session.commit()
