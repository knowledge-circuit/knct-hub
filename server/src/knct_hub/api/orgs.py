from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.session import get_session
from knct_hub.services.auth import (
    Caller,
    require_member,
    require_owner,
    resolve_caller,
)
from knct_hub.services.orgs import (
    create_org,
    get_org,
    list_members,
    list_orgs_for_user,
    remove_member,
    serialize_org,
    set_member_role,
)

router = APIRouter()


class OrgCreate(BaseModel):
    id: str
    name: str


class MemberRoleUpdate(BaseModel):
    role: str


@router.get("/orgs")
async def list_endpoint(
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    orgs = await list_orgs_for_user(session, caller.user_id)
    return [serialize_org(o) for o in orgs]


@router.post("/orgs", status_code=201)
async def create_endpoint(
    body: OrgCreate,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
) -> dict:
    org = await create_org(
        session, org_id=body.id, name=body.name, creator_user_id=caller.user_id
    )
    return serialize_org(org)


@router.get("/orgs/{org_id}")
async def get_endpoint(
    org_id: str,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
) -> dict:
    org = await get_org(session, org_id)
    return serialize_org(org)


@router.get("/orgs/{org_id}/members")
async def members_list(
    org_id: str,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await list_members(session, org_id)


@router.put("/orgs/{org_id}/members/{user_id}")
async def member_role_set(
    org_id: str,
    user_id: str,
    body: MemberRoleUpdate,
    _: Caller = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await set_member_role(session, org_id, user_id, body.role)


@router.delete("/orgs/{org_id}/members/{user_id}")
async def member_remove(
    org_id: str,
    user_id: str,
    _: Caller = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await remove_member(session, org_id, user_id)
    return {"ok": True}
