import re

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from knct_hub.db.models import Project

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


async def ensure_project(session: AsyncSession, slug: str) -> Project:
    result = await session.exec(select(Project).where(Project.slug == slug))
    project = result.first()
    if project is None:
        project = Project(slug=slug)
        session.add(project)
        await session.commit()
        await session.refresh(project)
    return project


async def list_projects(session: AsyncSession) -> list[Project]:
    result = await session.exec(select(Project).order_by(Project.created_at))
    return list(result.all())


async def create_project(session: AsyncSession, slug: str) -> Project:
    if not SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="invalid slug")
    existing = await session.exec(select(Project).where(Project.slug == slug))
    if existing.first():
        raise HTTPException(status_code=409, detail="slug already exists")
    project = Project(slug=slug)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project
