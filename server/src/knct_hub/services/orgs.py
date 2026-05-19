import json
import re

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import Org, OrgMember, User

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VALID_ROLES = ("owner", "admin", "member")


def serialize_org(org: Org) -> dict:
    return {
        "id": org.id,
        "name": org.name,
        "created_at": org.created_at.isoformat(),
        "default_bundles": json.loads(org.default_bundles or "[]"),
        "include_unbundled": bool(org.include_unbundled),
    }


async def list_orgs_for_user(session: AsyncSession, user_id: str) -> list[Org]:
    result = await session.exec(
        select(Org)
        .join(OrgMember, OrgMember.org_id == Org.id)
        .where(OrgMember.user_id == user_id)
        .order_by(Org.created_at)
    )
    return list(result.all())


async def get_org(session: AsyncSession, org_id: str) -> Org:
    result = await session.exec(select(Org).where(Org.id == org_id))
    org = result.first()
    if not org:
        raise HTTPException(status_code=404, detail="org not found")
    return org


async def create_org(
    session: AsyncSession, *, org_id: str, name: str, creator_user_id: str
) -> Org:
    if not SLUG_RE.match(org_id):
        raise HTTPException(status_code=400, detail="invalid org id")
    existing = await session.exec(select(Org).where(Org.id == org_id))
    if existing.first():
        raise HTTPException(status_code=409, detail="org id already exists")
    # Ensure user row exists (cloud auth creates this; for the stub we make it idempotent).
    user_result = await session.exec(select(User).where(User.id == creator_user_id))
    if not user_result.first():
        session.add(User(id=creator_user_id))
    org = Org(id=org_id, name=name)
    session.add(org)
    session.add(
        OrgMember(org_id=org_id, user_id=creator_user_id, role="owner")
    )
    await session.commit()
    await session.refresh(org)
    return org


async def update_org_default_bundles(
    session: AsyncSession, org_id: str, default_bundles: list[str]
) -> Org:
    org = await get_org(session, org_id)
    org.default_bundles = json.dumps(default_bundles)
    await session.commit()
    await session.refresh(org)
    return org


async def update_org_include_unbundled(
    session: AsyncSession, org_id: str, include_unbundled: bool
) -> Org:
    org = await get_org(session, org_id)
    org.include_unbundled = bool(include_unbundled)
    await session.commit()
    await session.refresh(org)
    return org


async def list_members(session: AsyncSession, org_id: str) -> list[dict]:
    await get_org(session, org_id)
    result = await session.exec(
        select(OrgMember).where(OrgMember.org_id == org_id).order_by(OrgMember.user_id)
    )
    return [
        {"user_id": m.user_id, "role": m.role, "created_at": m.created_at.isoformat()}
        for m in result.all()
    ]


async def _count_owners(session: AsyncSession, org_id: str) -> int:
    result = await session.exec(
        select(OrgMember).where(
            OrgMember.org_id == org_id, OrgMember.role == "owner"
        )
    )
    return len(list(result.all()))


async def set_member_role(
    session: AsyncSession, org_id: str, user_id: str, role: str
) -> dict:
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="invalid role")
    await get_org(session, org_id)
    result = await session.exec(
        select(OrgMember).where(
            OrgMember.org_id == org_id, OrgMember.user_id == user_id
        )
    )
    member = result.first()
    if not member:
        # Allow adding members by setting role for an existing user.
        user_result = await session.exec(select(User).where(User.id == user_id))
        if not user_result.first():
            raise HTTPException(status_code=404, detail="user not found")
        member = OrgMember(org_id=org_id, user_id=user_id, role=role)
        session.add(member)
        await session.commit()
        return {"user_id": user_id, "role": role}

    if member.role == "owner" and role != "owner":
        if await _count_owners(session, org_id) <= 1:
            raise HTTPException(
                status_code=409, detail="cannot demote the last owner"
            )
    member.role = role
    await session.commit()
    return {"user_id": user_id, "role": role}


async def remove_member(
    session: AsyncSession, org_id: str, user_id: str
) -> None:
    await get_org(session, org_id)
    result = await session.exec(
        select(OrgMember).where(
            OrgMember.org_id == org_id, OrgMember.user_id == user_id
        )
    )
    member = result.first()
    if not member:
        raise HTTPException(status_code=404, detail="member not found")
    if member.role == "owner" and await _count_owners(session, org_id) <= 1:
        raise HTTPException(
            status_code=409, detail="cannot remove the last owner"
        )
    await session.delete(member)
    await session.commit()
