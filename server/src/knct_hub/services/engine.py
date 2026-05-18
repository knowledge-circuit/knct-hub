import json
from datetime import datetime, timezone
from fnmatch import fnmatch

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from knct_hub.db.models import Rule, SessionDedupe


def _target_path(payload: dict) -> str:
    ti = payload.get("tool_input") or {}
    return ti.get("file_path") or payload.get("cwd") or ""


async def evaluate(
    session: AsyncSession, slug: str, on_event: str, payload: dict
) -> list[str]:
    session_id = payload.get("session_id") or ""
    target = _target_path(payload)

    rules_result = await session.exec(
        select(Rule)
        .where(Rule.project_slug == slug, Rule.on_event == on_event)
        .order_by(Rule.id)
    )
    rules = list(rules_result.all())
    if not rules:
        return []

    fired_result = await session.exec(
        select(SessionDedupe.rule_id).where(SessionDedupe.session_id == session_id)
    )
    fired = set(fired_result.all())

    selected: list[str] = []
    to_record: list[int] = []
    for rule in rules:
        if rule.match and not fnmatch(target, rule.match):
            continue
        if rule.once_per_session and rule.id in fired:
            continue
        selected.extend(json.loads(rule.inject or "[]"))
        if rule.once_per_session and rule.id is not None:
            to_record.append(rule.id)

    if to_record and session_id:
        now = datetime.now(timezone.utc)
        for rid in to_record:
            session.add(SessionDedupe(session_id=session_id, rule_id=rid, fired_at=now))
        await session.commit()

    return selected


async def clear_dedupe(session: AsyncSession, session_id: str) -> None:
    result = await session.exec(
        select(SessionDedupe).where(SessionDedupe.session_id == session_id)
    )
    for row in result.all():
        await session.delete(row)
    await session.commit()
