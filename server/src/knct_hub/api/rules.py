from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.session import get_session
from knct_hub.services.projects import ensure_project
from knct_hub.services.rules import (
    create_rule,
    delete_rule,
    list_rules,
    update_rule,
)

router = APIRouter()


class RuleBody(BaseModel):
    on_event: str
    match: str | None = None
    inject: list[str]
    once_per_session: bool | None = None


@router.get("/projects/{slug}/rules")
async def list_endpoint(
    slug: str, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    await ensure_project(session, slug)
    return await list_rules(session, slug)


@router.post("/projects/{slug}/rules", status_code=201)
async def create_endpoint(
    slug: str, body: RuleBody, session: AsyncSession = Depends(get_session)
) -> dict:
    await ensure_project(session, slug)
    return await create_rule(
        session,
        slug,
        on_event=body.on_event,
        match=body.match,
        inject=body.inject,
        once_per_session=body.once_per_session,
    )


@router.put("/projects/{slug}/rules/{rule_id}")
async def update_endpoint(
    slug: str,
    rule_id: int,
    body: RuleBody,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await update_rule(
        session,
        slug,
        rule_id,
        on_event=body.on_event,
        match=body.match,
        inject=body.inject,
        once_per_session=body.once_per_session,
    )


@router.delete("/projects/{slug}/rules/{rule_id}")
async def delete_endpoint(
    slug: str, rule_id: int, session: AsyncSession = Depends(get_session)
) -> dict:
    await delete_rule(session, slug, rule_id)
    return {"ok": True}
