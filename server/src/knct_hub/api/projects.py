from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.session import get_session
from knct_hub.services.projects import create_project, list_projects

router = APIRouter()


class ProjectCreate(BaseModel):
    slug: str


@router.get("/projects")
async def list_endpoint(
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    projects = await list_projects(session)
    return [
        {"slug": p.slug, "created_at": p.created_at.isoformat()} for p in projects
    ]


@router.post("/projects", status_code=201)
async def create_endpoint(
    body: ProjectCreate, session: AsyncSession = Depends(get_session)
) -> dict:
    project = await create_project(session, body.slug)
    return {"slug": project.slug, "created_at": project.created_at.isoformat()}
