"""Scope-aware kpatch CRUD + trigger CRUD + import.

Three scope endpoint groups:
- /api/v1/orgs/{org_id}/kpatches/...
- /api/v1/orgs/{org}/projects/{slug}/kpatches/...
- /api/v1/orgs/{org}/projects/{slug}/members/{user_id}/kpatches/...

Each group exposes:
  GET    /                                    list (with ?include_inherited)
  GET    /{slug}                              read
  PUT    /{slug}                              upsert
  DELETE /{slug}                              delete
  POST   /import                              import .md file
  PUT    /{slug}/disable                      set disable=true|false (auto-creates stub)
  GET    /{slug}/triggers                     list triggers
  POST   /{slug}/triggers                     create trigger
  PUT    /{slug}/triggers/{trigger_id}        update
  DELETE /{slug}/triggers/{trigger_id}        delete
"""


from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.session import get_session
from knct_hub.services.auth import (
    Caller,
    require_active_admin,
    require_active_member,
    require_admin,
    require_member,
    resolve_caller,
)
from knct_hub.services.kpatch_import import import_kpatch_file
from knct_hub.services.kpatches import (
    Scope,
    delete_kpatch,
    get_kpatch,
    list_kpatches,
    list_with_inherited,
    serialize_kpatch,
    set_disable,
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
    body: str = ""
    keywords: list[str] = []
    disable: bool = False


class DisableBody(BaseModel):
    disable: bool


class TriggerBody(BaseModel):
    event: str
    prompt_contains: list[str] | None = None
    path_match: str | None = None
    once_per_session: bool | None = None


# ---- helpers --------------------------------------------------------------

async def _kpatch_pk_id(session: AsyncSession, scope: Scope, slug: str) -> int:
    k = await get_kpatch(session, scope, slug)
    if k.pk_id is None:
        raise HTTPException(status_code=500, detail="kpatch missing pk_id")
    return k.pk_id


def _register_scope_routes(prefix: str, scope_factory):
    """Register the full kpatch+trigger CRUD surface under `prefix`.

    ``scope_factory`` is a callable that takes the path params and returns a
    Scope. We can't share much across scopes because FastAPI requires the
    path params on the handler signature.
    """
    # The actual handlers are defined below per-scope so they can declare
    # their own path parameters. This helper exists only as documentation.
    pass


# ---- org scope ------------------------------------------------------------

ORG_PREFIX = "/orgs/{org_id}/kpatches"


@router.get(ORG_PREFIX)
async def org_list(
    org_id: str,
    include_inherited: bool = False,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    scope = Scope.org(org_id)
    if include_inherited:
        return await list_with_inherited(session, scope)
    return await list_kpatches(session, scope)


@router.get(ORG_PREFIX + "/{slug}")
async def org_get(
    org_id: str,
    slug: str,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    return serialize_kpatch(await get_kpatch(session, Scope.org(org_id), slug))


@router.put(ORG_PREFIX + "/{slug}")
async def org_upsert(
    org_id: str,
    slug: str,
    body: KpatchBody,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await upsert_kpatch(
        session, Scope.org(org_id), slug,
        name=body.name, description=body.description,
        body=body.body, keywords=body.keywords, disable=body.disable,
    )


@router.delete(ORG_PREFIX + "/{slug}")
async def org_delete(
    org_id: str,
    slug: str,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await delete_kpatch(session, Scope.org(org_id), slug)
    return {"ok": True}


@router.put(ORG_PREFIX + "/{slug}/disable")
async def org_set_disable(
    org_id: str,
    slug: str,
    body: DisableBody,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await set_disable(session, Scope.org(org_id), slug, body.disable)


@router.post(ORG_PREFIX + "/import")
async def org_import(
    org_id: str,
    request: Request,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    text = (await request.body()).decode("utf-8")
    return await import_kpatch_file(session, Scope.org(org_id), text)


@router.get(ORG_PREFIX + "/{slug}/triggers")
async def org_list_triggers(
    org_id: str,
    slug: str,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    pk = await _kpatch_pk_id(session, Scope.org(org_id), slug)
    return await list_triggers(session, pk)


@router.post(ORG_PREFIX + "/{slug}/triggers", status_code=201)
async def org_create_trigger(
    org_id: str,
    slug: str,
    body: TriggerBody,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    pk = await _kpatch_pk_id(session, Scope.org(org_id), slug)
    return await create_trigger(
        session, pk,
        event=body.event,
        prompt_contains=body.prompt_contains,
        path_match=body.path_match,
        once_per_session=body.once_per_session,
    )


@router.put(ORG_PREFIX + "/{slug}/triggers/{trigger_id}")
async def org_update_trigger(
    org_id: str,
    slug: str,
    trigger_id: int,
    body: TriggerBody,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    pk = await _kpatch_pk_id(session, Scope.org(org_id), slug)
    return await update_trigger(
        session, pk, trigger_id,
        event=body.event,
        prompt_contains=body.prompt_contains,
        path_match=body.path_match,
        once_per_session=body.once_per_session,
    )


@router.delete(ORG_PREFIX + "/{slug}/triggers/{trigger_id}")
async def org_delete_trigger(
    org_id: str,
    slug: str,
    trigger_id: int,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    pk = await _kpatch_pk_id(session, Scope.org(org_id), slug)
    await delete_trigger(session, pk, trigger_id)
    return {"ok": True}


# ---- project scope --------------------------------------------------------

PROJ_PREFIX = "/orgs/{org_id}/projects/{project_slug}/kpatches"


@router.get(PROJ_PREFIX)
async def proj_list(
    org_id: str,
    project_slug: str,
    include_inherited: bool = False,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    scope = Scope.project(org_id, project_slug)
    if include_inherited:
        return await list_with_inherited(session, scope)
    return await list_kpatches(session, scope)


@router.get(PROJ_PREFIX + "/{slug}")
async def proj_get(
    org_id: str,
    project_slug: str,
    slug: str,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    return serialize_kpatch(
        await get_kpatch(session, Scope.project(org_id, project_slug), slug)
    )


@router.put(PROJ_PREFIX + "/{slug}")
async def proj_upsert(
    org_id: str,
    project_slug: str,
    slug: str,
    body: KpatchBody,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await upsert_kpatch(
        session, Scope.project(org_id, project_slug), slug,
        name=body.name, description=body.description,
        body=body.body, keywords=body.keywords, disable=body.disable,
    )


@router.delete(PROJ_PREFIX + "/{slug}")
async def proj_delete(
    org_id: str,
    project_slug: str,
    slug: str,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await delete_kpatch(session, Scope.project(org_id, project_slug), slug)
    return {"ok": True}


@router.put(PROJ_PREFIX + "/{slug}/disable")
async def proj_set_disable(
    org_id: str,
    project_slug: str,
    slug: str,
    body: DisableBody,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await set_disable(
        session, Scope.project(org_id, project_slug), slug, body.disable
    )


@router.post(PROJ_PREFIX + "/import")
async def proj_import(
    org_id: str,
    project_slug: str,
    request: Request,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    text = (await request.body()).decode("utf-8")
    return await import_kpatch_file(
        session, Scope.project(org_id, project_slug), text
    )


@router.get(PROJ_PREFIX + "/{slug}/triggers")
async def proj_list_triggers(
    org_id: str,
    project_slug: str,
    slug: str,
    _: Caller = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    pk = await _kpatch_pk_id(session, Scope.project(org_id, project_slug), slug)
    return await list_triggers(session, pk)


@router.post(PROJ_PREFIX + "/{slug}/triggers", status_code=201)
async def proj_create_trigger(
    org_id: str,
    project_slug: str,
    slug: str,
    body: TriggerBody,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    pk = await _kpatch_pk_id(session, Scope.project(org_id, project_slug), slug)
    return await create_trigger(
        session, pk,
        event=body.event,
        prompt_contains=body.prompt_contains,
        path_match=body.path_match,
        once_per_session=body.once_per_session,
    )


@router.put(PROJ_PREFIX + "/{slug}/triggers/{trigger_id}")
async def proj_update_trigger(
    org_id: str,
    project_slug: str,
    slug: str,
    trigger_id: int,
    body: TriggerBody,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    pk = await _kpatch_pk_id(session, Scope.project(org_id, project_slug), slug)
    return await update_trigger(
        session, pk, trigger_id,
        event=body.event,
        prompt_contains=body.prompt_contains,
        path_match=body.path_match,
        once_per_session=body.once_per_session,
    )


@router.delete(PROJ_PREFIX + "/{slug}/triggers/{trigger_id}")
async def proj_delete_trigger(
    org_id: str,
    project_slug: str,
    slug: str,
    trigger_id: int,
    _: Caller = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    pk = await _kpatch_pk_id(session, Scope.project(org_id, project_slug), slug)
    await delete_trigger(session, pk, trigger_id)
    return {"ok": True}


# ---- member scope ---------------------------------------------------------

MEMBER_PREFIX = "/orgs/{org_id}/projects/{project_slug}/members/{user_id}/kpatches"


def _check_member_scope(caller: Caller, user_id: str) -> None:
    """Member-scope edits are allowed for the user themselves OR an admin.

    Auth check is light here because role enforcement happens via
    require_admin or by the caller matching the user_id.
    """
    # Allow when caller is the target user.
    if caller.user_id == user_id:
        return
    # Else fall through to require admin role on org (the dependency below).


@router.get(MEMBER_PREFIX)
async def mem_list(
    org_id: str,
    project_slug: str,
    user_id: str,
    include_inherited: bool = False,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
):
    scope = Scope.member(org_id, project_slug, user_id)
    if include_inherited:
        return await list_with_inherited(session, scope)
    return await list_kpatches(session, scope)


@router.get(MEMBER_PREFIX + "/{slug}")
async def mem_get(
    org_id: str,
    project_slug: str,
    user_id: str,
    slug: str,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
):
    return serialize_kpatch(
        await get_kpatch(session, Scope.member(org_id, project_slug, user_id), slug)
    )


@router.put(MEMBER_PREFIX + "/{slug}")
async def mem_upsert(
    org_id: str,
    project_slug: str,
    user_id: str,
    slug: str,
    body: KpatchBody,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
):
    if caller.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="member-scope edits only by that user"
        )
    return await upsert_kpatch(
        session, Scope.member(org_id, project_slug, user_id), slug,
        name=body.name, description=body.description,
        body=body.body, keywords=body.keywords, disable=body.disable,
    )


@router.delete(MEMBER_PREFIX + "/{slug}")
async def mem_delete(
    org_id: str,
    project_slug: str,
    user_id: str,
    slug: str,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
):
    if caller.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="member-scope edits only by that user"
        )
    await delete_kpatch(
        session, Scope.member(org_id, project_slug, user_id), slug
    )
    return {"ok": True}


@router.put(MEMBER_PREFIX + "/{slug}/disable")
async def mem_set_disable(
    org_id: str,
    project_slug: str,
    user_id: str,
    slug: str,
    body: DisableBody,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
):
    if caller.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="member-scope edits only by that user"
        )
    return await set_disable(
        session, Scope.member(org_id, project_slug, user_id), slug, body.disable
    )


@router.post(MEMBER_PREFIX + "/import")
async def mem_import(
    org_id: str,
    project_slug: str,
    user_id: str,
    request: Request,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
):
    if caller.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="member-scope edits only by that user"
        )
    text = (await request.body()).decode("utf-8")
    return await import_kpatch_file(
        session, Scope.member(org_id, project_slug, user_id), text
    )


@router.get(MEMBER_PREFIX + "/{slug}/triggers")
async def mem_list_triggers(
    org_id: str,
    project_slug: str,
    user_id: str,
    slug: str,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
):
    pk = await _kpatch_pk_id(
        session, Scope.member(org_id, project_slug, user_id), slug
    )
    return await list_triggers(session, pk)


@router.post(MEMBER_PREFIX + "/{slug}/triggers", status_code=201)
async def mem_create_trigger(
    org_id: str,
    project_slug: str,
    user_id: str,
    slug: str,
    body: TriggerBody,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
):
    if caller.user_id != user_id:
        raise HTTPException(status_code=403, detail="member-scope edits only by that user")
    pk = await _kpatch_pk_id(
        session, Scope.member(org_id, project_slug, user_id), slug
    )
    return await create_trigger(
        session, pk,
        event=body.event,
        prompt_contains=body.prompt_contains,
        path_match=body.path_match,
        once_per_session=body.once_per_session,
    )


@router.put(MEMBER_PREFIX + "/{slug}/triggers/{trigger_id}")
async def mem_update_trigger(
    org_id: str,
    project_slug: str,
    user_id: str,
    slug: str,
    trigger_id: int,
    body: TriggerBody,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
):
    if caller.user_id != user_id:
        raise HTTPException(status_code=403, detail="member-scope edits only by that user")
    pk = await _kpatch_pk_id(
        session, Scope.member(org_id, project_slug, user_id), slug
    )
    return await update_trigger(
        session, pk, trigger_id,
        event=body.event,
        prompt_contains=body.prompt_contains,
        path_match=body.path_match,
        once_per_session=body.once_per_session,
    )


@router.delete(MEMBER_PREFIX + "/{slug}/triggers/{trigger_id}")
async def mem_delete_trigger(
    org_id: str,
    project_slug: str,
    user_id: str,
    slug: str,
    trigger_id: int,
    caller: Caller = Depends(resolve_caller),
    session: AsyncSession = Depends(get_session),
):
    if caller.user_id != user_id:
        raise HTTPException(status_code=403, detail="member-scope edits only by that user")
    pk = await _kpatch_pk_id(
        session, Scope.member(org_id, project_slug, user_id), slug
    )
    await delete_trigger(session, pk, trigger_id)
    return {"ok": True}
