from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.session import get_session
from knct_hub.services.auth import Caller, require_admin, require_member
from knct_hub.services.bundles import (
    delete_bundle,
    get_bundle,
    list_bundles,
    serialize_bundle,
    upsert_bundle,
)

router = APIRouter()


class BundleBody(BaseModel):
    name: str
    version: str
    kpatch_ids: list[str] = []


@router.get("/orgs/{org_id}/bundles")
async def list_endpoint(
    org_id: str,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await list_bundles(session, org_id)


@router.get("/orgs/{org_id}/bundles/{bundle_id}")
async def get_endpoint(
    org_id: str,
    bundle_id: str,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return serialize_bundle(await get_bundle(session, org_id, bundle_id))


@router.put("/orgs/{org_id}/bundles/{bundle_id}")
async def put_endpoint(
    org_id: str,
    bundle_id: str,
    body: BundleBody,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await upsert_bundle(
        session,
        org_id,
        bundle_id,
        name=body.name,
        version=body.version,
        kpatch_ids=body.kpatch_ids,
    )


@router.delete("/orgs/{org_id}/bundles/{bundle_id}")
async def delete_endpoint(
    org_id: str,
    bundle_id: str,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await delete_bundle(session, org_id, bundle_id)
    return {"ok": True}
