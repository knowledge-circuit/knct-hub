"""Trigger evaluation.

Consumes the effective kpatch set from `resolver.resolve_effective_kpatches`
and decides which kpatch bodies to inject for a given hook event.

Per-session dedupe is preserved from the legacy rule-engine but keyed on
trigger_id. Override-materialized triggers have `id=None` and are not
deduped (they exist only in-memory for the duration of this request).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from fnmatch import fnmatch
from typing import Iterable

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import SessionDedupe, Trigger
from knct_hub.services.resolver import EffectiveKpatch


def _target_path(payload: dict) -> str:
    ti = payload.get("tool_input") or {}
    return ti.get("file_path") or payload.get("cwd") or ""


def _prompt_text(payload: dict) -> str:
    return (payload.get("prompt") or "").lower()


def _matches(trigger: Trigger, event: str, payload: dict) -> bool:
    if trigger.event != event:
        return False
    if trigger.path_match:
        if not fnmatch(_target_path(payload), trigger.path_match):
            return False
    if event == "user_prompt" and trigger.prompt_contains:
        needles = json.loads(trigger.prompt_contains)
        if needles:
            prompt = _prompt_text(payload)
            if not any(n and n.lower() in prompt for n in needles):
                return False
    return True


async def _fired_trigger_ids(
    session: AsyncSession, session_id: str
) -> set[int]:
    if not session_id:
        return set()
    result = await session.exec(
        select(SessionDedupe.trigger_id).where(
            SessionDedupe.session_id == session_id
        )
    )
    return set(result.all())


async def select_kpatches(
    session: AsyncSession,
    effective: Iterable[EffectiveKpatch],
    event: str,
    payload: dict,
) -> list[EffectiveKpatch]:
    """Return the ordered list of kpatches whose triggers fired for this event."""
    session_id = payload.get("session_id") or ""
    fired = await _fired_trigger_ids(session, session_id)

    selected: list[EffectiveKpatch] = []
    to_record: list[int] = []
    for ek in effective:
        chose_this = False
        for trigger in ek.triggers:
            if not _matches(trigger, event, payload):
                continue
            if (
                trigger.once_per_session
                and trigger.id is not None
                and trigger.id in fired
            ):
                continue
            chose_this = True
            if trigger.once_per_session and trigger.id is not None:
                to_record.append(trigger.id)
        if chose_this:
            selected.append(ek)

    if to_record and session_id:
        now = datetime.now(timezone.utc)
        for tid in to_record:
            session.add(
                SessionDedupe(session_id=session_id, trigger_id=tid, fired_at=now)
            )
        await session.commit()

    return selected


async def clear_dedupe(session: AsyncSession, session_id: str) -> None:
    result = await session.exec(
        select(SessionDedupe).where(SessionDedupe.session_id == session_id)
    )
    for row in result.all():
        await session.delete(row)
    await session.commit()
