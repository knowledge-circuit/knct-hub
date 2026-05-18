from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.session import get_session
from knct_hub.services.projects import ensure_project
from knct_hub.services.skills import (
    delete_skill,
    get_skill,
    list_skills,
    upsert_skill,
)

router = APIRouter()


class SkillBody(BaseModel):
    name: str
    description: str | None = None
    body: str
    keywords: list[str] = []


@router.get("/projects/{slug}/skills")
async def list_endpoint(
    slug: str, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    await ensure_project(session, slug)
    return await list_skills(session, slug)


@router.get("/projects/{slug}/skills/{skill_id}")
async def get_endpoint(
    slug: str, skill_id: str, session: AsyncSession = Depends(get_session)
) -> dict:
    return await get_skill(session, slug, skill_id)


@router.put("/projects/{slug}/skills/{skill_id}")
async def put_endpoint(
    slug: str,
    skill_id: str,
    body: SkillBody,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await ensure_project(session, slug)
    return await upsert_skill(
        session,
        slug,
        skill_id,
        name=body.name,
        description=body.description,
        body=body.body,
        keywords=body.keywords,
    )


@router.delete("/projects/{slug}/skills/{skill_id}")
async def delete_endpoint(
    slug: str, skill_id: str, session: AsyncSession = Depends(get_session)
) -> dict:
    await delete_skill(session, slug, skill_id)
    return {"ok": True}
