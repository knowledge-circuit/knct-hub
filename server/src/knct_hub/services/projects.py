import json
import re

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import Org, Project

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VALID_ACCESS = ("org", "invite_only")


def serialize_project(p: Project) -> dict:
    return {
        "slug": p.slug,
        "org_id": p.org_id,
        "created_at": p.created_at.isoformat(),
        "access_mode": p.access_mode,
        "members": json.loads(p.members or "[]"),
    }


async def _ensure_org(session: AsyncSession, org_id: str) -> None:
    result = await session.exec(select(Org).where(Org.id == org_id))
    if not result.first():
        raise HTTPException(status_code=404, detail="org not found")


async def list_projects(session: AsyncSession, org_id: str) -> list[Project]:
    await _ensure_org(session, org_id)
    result = await session.exec(
        select(Project)
        .where(Project.org_id == org_id)
        .order_by(Project.created_at)
    )
    return list(result.all())


async def get_project(
    session: AsyncSession, org_id: str, slug: str
) -> Project:
    result = await session.exec(
        select(Project).where(Project.org_id == org_id, Project.slug == slug)
    )
    p = result.first()
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    return p


async def create_project(
    session: AsyncSession, org_id: str, slug: str
) -> Project:
    if not SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="invalid slug")
    await _ensure_org(session, org_id)
    existing = await session.exec(
        select(Project).where(Project.org_id == org_id, Project.slug == slug)
    )
    if existing.first():
        raise HTTPException(status_code=409, detail="slug already exists")
    project = Project(org_id=org_id, slug=slug)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def ensure_project(
    session: AsyncSession, org_id: str, slug: str
) -> Project:
    await _ensure_org(session, org_id)
    result = await session.exec(
        select(Project).where(Project.org_id == org_id, Project.slug == slug)
    )
    project = result.first()
    if project is None:
        if not SLUG_RE.match(slug):
            raise HTTPException(status_code=400, detail="invalid slug")
        project = Project(org_id=org_id, slug=slug)
        session.add(project)
        await session.commit()
        await session.refresh(project)
    return project


def _members_list(project: Project) -> list[str]:
    return json.loads(project.members or "[]")


async def authorize_hook(
    session: AsyncSession, project: Project, user_id: str
) -> Project:
    members = _members_list(project)
    if project.access_mode == "invite_only":
        if user_id not in members:
            raise HTTPException(
                status_code=403, detail="not a member of this project"
            )
        return project
    if user_id not in members:
        members.append(user_id)
        project.members = json.dumps(members)
        await session.commit()
        await session.refresh(project)
    return project


async def update_access(
    session: AsyncSession,
    org_id: str,
    slug: str,
    *,
    access_mode: str | None,
    members: list[str] | None,
) -> Project:
    if access_mode is not None and access_mode not in VALID_ACCESS:
        raise HTTPException(status_code=400, detail="invalid access_mode")
    project = await get_project(session, org_id, slug)
    if access_mode is not None:
        project.access_mode = access_mode
    if members is not None:
        seen: set[str] = set()
        out: list[str] = []
        for m in members:
            if m and m not in seen:
                seen.add(m)
                out.append(m)
        project.members = json.dumps(out)
    await session.commit()
    await session.refresh(project)
    return project
