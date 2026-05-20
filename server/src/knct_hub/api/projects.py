from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.session import get_session
from knct_hub.services.auth import (
    Caller,
    require_active_admin,
    require_active_member,
    require_admin,
    require_member,
)
from knct_hub.services.projects import (
    create_project,
    get_project,
    list_projects,
    serialize_project,
    update_access,
)

router = APIRouter()


class ProjectCreate(BaseModel):
    slug: str


class AccessUpdate(BaseModel):
    access_mode: str | None = None
    members: list[str] | None = None


@router.get("/orgs/{org_id}/projects")
async def list_endpoint(
    org_id: str,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    projects = await list_projects(session, org_id)
    return [serialize_project(p) for p in projects]


@router.post("/orgs/{org_id}/projects", status_code=201)
async def create_endpoint(
    org_id: str,
    body: ProjectCreate,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    project = await create_project(session, org_id, body.slug)
    return serialize_project(project)


@router.get("/projects/{slug}")
async def get_endpoint(
    slug: str,
    caller: Caller = Depends(require_active_member),
    session: AsyncSession = Depends(get_session),
) -> dict:
    project = await get_project(session, caller.active_org_id, slug)
    return serialize_project(project)


@router.get("/projects/{slug}/access")
async def get_access(
    slug: str,
    caller: Caller = Depends(require_active_member),
    session: AsyncSession = Depends(get_session),
) -> dict:
    project = await get_project(session, caller.active_org_id, slug)
    return {
        "access_mode": project.access_mode,
        "members": serialize_project(project)["members"],
    }


@router.put("/projects/{slug}/access")
async def put_access(
    slug: str,
    body: AccessUpdate,
    caller: Caller = Depends(require_active_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    project = await update_access(
        session,
        caller.active_org_id,
        slug,
        access_mode=body.access_mode,
        members=body.members,
    )
    return serialize_project(project)
