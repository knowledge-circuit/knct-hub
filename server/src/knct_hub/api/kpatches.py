from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.session import get_session
from knct_hub.services.auth import Caller, require_admin, require_member
from knct_hub.services.kpatch_import import import_kpatch_file
from knct_hub.services.kpatches import (
    delete_kpatch,
    get_kpatch,
    list_kpatches,
    serialize_kpatch,
    upsert_kpatch,
)
from knct_hub.services.triggers import (
    create_trigger,
    delete_trigger,
    list_triggers,
    update_trigger,
)

router = APIRouter()


class KpatchBody(BaseModel):
    name: str
    description: str | None = None
    body: str
    keywords: list[str] = []


class TriggerBody(BaseModel):
    event: str
    prompt_contains: list[str] | None = None
    path_match: str | None = None
    once_per_session: bool | None = None


@router.get("/orgs/{org_id}/kpatches")
async def list_kpatches_endpoint(
    org_id: str,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await list_kpatches(session, org_id)


@router.get("/orgs/{org_id}/kpatches/{kpatch_id}")
async def get_kpatch_endpoint(
    org_id: str,
    kpatch_id: str,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return serialize_kpatch(await get_kpatch(session, org_id, kpatch_id))


@router.put("/orgs/{org_id}/kpatches/{kpatch_id}")
async def put_kpatch_endpoint(
    org_id: str,
    kpatch_id: str,
    body: KpatchBody,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await upsert_kpatch(
        session,
        org_id,
        kpatch_id,
        name=body.name,
        description=body.description,
        body=body.body,
        keywords=body.keywords,
    )


@router.delete("/orgs/{org_id}/kpatches/{kpatch_id}")
async def delete_kpatch_endpoint(
    org_id: str,
    kpatch_id: str,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await delete_kpatch(session, org_id, kpatch_id)
    return {"ok": True}


@router.post("/orgs/{org_id}/kpatches/import", status_code=200)
async def import_endpoint(
    org_id: str,
    request: Request,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    text = (await request.body()).decode("utf-8")
    return await import_kpatch_file(session, org_id, text)


@router.get("/orgs/{org_id}/kpatches/{kpatch_id}/triggers")
async def list_triggers_endpoint(
    org_id: str,
    kpatch_id: str,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await list_triggers(session, org_id, kpatch_id)


@router.post(
    "/orgs/{org_id}/kpatches/{kpatch_id}/triggers", status_code=201
)
async def create_trigger_endpoint(
    org_id: str,
    kpatch_id: str,
    body: TriggerBody,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await create_trigger(
        session,
        org_id,
        kpatch_id,
        event=body.event,
        prompt_contains=body.prompt_contains,
        path_match=body.path_match,
        once_per_session=body.once_per_session,
    )


@router.put(
    "/orgs/{org_id}/kpatches/{kpatch_id}/triggers/{trigger_id}"
)
async def update_trigger_endpoint(
    org_id: str,
    kpatch_id: str,
    trigger_id: int,
    body: TriggerBody,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await update_trigger(
        session,
        org_id,
        kpatch_id,
        trigger_id,
        event=body.event,
        prompt_contains=body.prompt_contains,
        path_match=body.path_match,
        once_per_session=body.once_per_session,
    )


@router.delete(
    "/orgs/{org_id}/kpatches/{kpatch_id}/triggers/{trigger_id}"
)
async def delete_trigger_endpoint(
    org_id: str,
    kpatch_id: str,
    trigger_id: int,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await delete_trigger(session, org_id, kpatch_id, trigger_id)
    return {"ok": True}
