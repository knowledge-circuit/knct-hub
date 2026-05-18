import json

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from knct_hub.db.models import Skill


def _serialize(skill: Skill) -> dict:
    return {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "body": skill.body,
        "keywords": json.loads(skill.keywords or "[]"),
    }


async def list_skills(session: AsyncSession, slug: str) -> list[dict]:
    result = await session.exec(
        select(Skill).where(Skill.project_slug == slug).order_by(Skill.id)
    )
    return [_serialize(s) for s in result.all()]


async def get_skill(session: AsyncSession, slug: str, skill_id: str) -> dict:
    result = await session.exec(
        select(Skill).where(Skill.project_slug == slug, Skill.id == skill_id)
    )
    skill = result.first()
    if not skill:
        raise HTTPException(status_code=404, detail="skill not found")
    return _serialize(skill)


async def upsert_skill(
    session: AsyncSession,
    slug: str,
    skill_id: str,
    *,
    name: str,
    description: str | None,
    body: str,
    keywords: list[str],
) -> dict:
    result = await session.exec(
        select(Skill).where(Skill.project_slug == slug, Skill.id == skill_id)
    )
    skill = result.first()
    if skill:
        skill.name = name
        skill.description = description
        skill.body = body
        skill.keywords = json.dumps(keywords)
    else:
        skill = Skill(
            project_slug=slug,
            id=skill_id,
            name=name,
            description=description,
            body=body,
            keywords=json.dumps(keywords),
        )
        session.add(skill)
    await session.commit()
    await session.refresh(skill)
    return _serialize(skill)


async def delete_skill(session: AsyncSession, slug: str, skill_id: str) -> None:
    result = await session.exec(
        select(Skill).where(Skill.project_slug == slug, Skill.id == skill_id)
    )
    skill = result.first()
    if not skill:
        raise HTTPException(status_code=404, detail="skill not found")
    await session.delete(skill)
    await session.commit()
