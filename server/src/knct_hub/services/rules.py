import json

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from knct_hub.db.models import Rule


def _serialize(rule: Rule) -> dict:
    return {
        "id": rule.id,
        "on_event": rule.on_event,
        "match": rule.match,
        "inject": json.loads(rule.inject or "[]"),
        "once_per_session": rule.once_per_session,
    }


def _normalize_once(on_event: str, once: bool | None) -> bool:
    if once is not None:
        return once
    return on_event == "pre_read"


async def list_rules(session: AsyncSession, slug: str) -> list[dict]:
    result = await session.exec(
        select(Rule).where(Rule.project_slug == slug).order_by(Rule.id)
    )
    return [_serialize(r) for r in result.all()]


async def create_rule(
    session: AsyncSession,
    slug: str,
    *,
    on_event: str,
    match: str | None,
    inject: list[str],
    once_per_session: bool | None,
) -> dict:
    rule = Rule(
        project_slug=slug,
        on_event=on_event,
        match=match,
        inject=json.dumps(inject),
        once_per_session=_normalize_once(on_event, once_per_session),
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return _serialize(rule)


async def update_rule(
    session: AsyncSession,
    slug: str,
    rule_id: int,
    *,
    on_event: str,
    match: str | None,
    inject: list[str],
    once_per_session: bool | None,
) -> dict:
    result = await session.exec(
        select(Rule).where(Rule.project_slug == slug, Rule.id == rule_id)
    )
    rule = result.first()
    if not rule:
        raise HTTPException(status_code=404, detail="rule not found")
    rule.on_event = on_event
    rule.match = match
    rule.inject = json.dumps(inject)
    rule.once_per_session = _normalize_once(on_event, once_per_session)
    await session.commit()
    await session.refresh(rule)
    return _serialize(rule)


async def delete_rule(session: AsyncSession, slug: str, rule_id: int) -> None:
    result = await session.exec(
        select(Rule).where(Rule.project_slug == slug, Rule.id == rule_id)
    )
    rule = result.first()
    if not rule:
        raise HTTPException(status_code=404, detail="rule not found")
    await session.delete(rule)
    await session.commit()
