"""Caller resolution and role checks.

This is a Track-A stub. Real Clerk + device-token middleware lands in
group 3 (auth-clerk, device-token capabilities); when it does, only the
``resolve_caller`` body changes — endpoints keep depending on the same
``Caller`` shape.

For now the caller defaults to the solo user/org. Two optional headers
let cloud-dev tests pretend to be someone else without standing up
Clerk:

    X-Knct-User: <user id>
    X-Knct-Org:  <org id>

There is no signature on these headers; they MUST NOT be trusted in
production. The middleware that replaces this stub will refuse to honor
them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import OrgMember
from knct_hub.db.session import get_session


@dataclass
class Caller:
    user_id: str
    # The user's *active* org for this request (resolved from header or default).
    # Role within that org is fetched on demand via ``role_in``.
    active_org_id: str


async def resolve_caller(
    x_knct_user: Optional[str] = Header(default=None, alias="X-Knct-User"),
    x_knct_org: Optional[str] = Header(default=None, alias="X-Knct-Org"),
) -> Caller:
    return Caller(
        user_id=x_knct_user or "solo",
        active_org_id=x_knct_org or "solo",
    )


async def role_in(
    session: AsyncSession, user_id: str, org_id: str
) -> Optional[str]:
    result = await session.exec(
        select(OrgMember).where(
            OrgMember.org_id == org_id, OrgMember.user_id == user_id
        )
    )
    row = result.first()
    return row.role if row else None


async def require_member(
    org_id: str,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
) -> Caller:
    role = await role_in(session, caller.user_id, org_id)
    if role is None:
        raise HTTPException(status_code=403, detail="not a member of this org")
    return caller


async def require_admin(
    org_id: str,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
) -> Caller:
    role = await role_in(session, caller.user_id, org_id)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="admin or owner role required")
    return caller


async def require_owner(
    org_id: str,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
) -> Caller:
    role = await role_in(session, caller.user_id, org_id)
    if role != "owner":
        raise HTTPException(status_code=403, detail="owner role required")
    return caller


# Variants for endpoints that don't carry org_id in the URL — they use
# the caller's active org instead. Used by /projects/{slug}/... routes.
async def require_active_member(
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
) -> Caller:
    role = await role_in(session, caller.user_id, caller.active_org_id)
    if role is None:
        raise HTTPException(status_code=403, detail="not a member of this org")
    return caller


async def require_active_admin(
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
) -> Caller:
    role = await role_in(session, caller.user_id, caller.active_org_id)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="admin or owner role required")
    return caller
