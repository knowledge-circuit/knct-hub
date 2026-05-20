"""Scope-aware kpatch CRUD.

Each kpatch lives at exactly one scope. The 5-tuple
(scope, org_id, project_slug, user_id, slug) is unique. Use the
``SCOPE_*`` constants from ``db.models`` for callers; service functions
keep the empty-string sentinels (``""``) internal so consumers don't
have to think about them.
"""


import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import (
    NOT_APPLICABLE,
    SCOPE_MEMBER,
    SCOPE_ORG,
    SCOPE_PROJECT,
    Kpatch,
    Org,
    Trigger,
)

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VALID_SCOPES = (SCOPE_ORG, SCOPE_PROJECT, SCOPE_MEMBER)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Scope:
    scope: str
    org_id: str
    project_slug: str = NOT_APPLICABLE
    user_id: str = NOT_APPLICABLE

    @classmethod
    def org(cls, org_id: str) -> "Scope":
        return cls(scope=SCOPE_ORG, org_id=org_id)

    @classmethod
    def project(cls, org_id: str, project_slug: str) -> "Scope":
        return cls(scope=SCOPE_PROJECT, org_id=org_id, project_slug=project_slug)

    @classmethod
    def member(cls, org_id: str, project_slug: str, user_id: str) -> "Scope":
        return cls(
            scope=SCOPE_MEMBER,
            org_id=org_id,
            project_slug=project_slug,
            user_id=user_id,
        )


def serialize_kpatch(k: Kpatch) -> dict:
    return {
        "pk_id": k.pk_id,
        "scope": k.scope,
        "org_id": k.org_id,
        "project_slug": k.project_slug or None,
        "user_id": k.user_id or None,
        "slug": k.slug,
        "disable": bool(k.disable),
        "name": k.name,
        "description": k.description,
        "body": k.body,
        "keywords": json.loads(k.keywords or "[]"),
        "created_at": k.created_at.isoformat(),
        "updated_at": k.updated_at.isoformat(),
    }


def _normalize_keywords(keywords: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for k in keywords or []:
        k = (k or "").strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


async def _ensure_org(session: AsyncSession, org_id: str) -> None:
    result = await session.exec(select(Org).where(Org.id == org_id))
    if not result.first():
        raise HTTPException(status_code=404, detail="org not found")


def _scope_filter(q, scope: Scope):
    return q.where(
        Kpatch.scope == scope.scope,
        Kpatch.org_id == scope.org_id,
        Kpatch.project_slug == scope.project_slug,
        Kpatch.user_id == scope.user_id,
    )


async def list_kpatches(session: AsyncSession, scope: Scope) -> list[dict]:
    await _ensure_org(session, scope.org_id)
    q = _scope_filter(select(Kpatch), scope).order_by(Kpatch.slug)
    result = await session.exec(q)
    return [serialize_kpatch(k) for k in result.all()]


async def get_kpatch(
    session: AsyncSession, scope: Scope, slug: str
) -> Kpatch:
    q = _scope_filter(select(Kpatch), scope).where(Kpatch.slug == slug)
    result = await session.exec(q)
    k = result.first()
    if not k:
        raise HTTPException(status_code=404, detail="kpatch not found")
    return k


async def upsert_kpatch(
    session: AsyncSession,
    scope: Scope,
    slug: str,
    *,
    name: str,
    description: str | None,
    body: str,
    keywords: list[str],
    disable: bool = False,
) -> dict:
    if not SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="invalid kpatch slug")
    if scope.scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail="invalid scope")
    await _ensure_org(session, scope.org_id)

    q = _scope_filter(select(Kpatch), scope).where(Kpatch.slug == slug)
    result = await session.exec(q)
    k = result.first()
    keywords_json = json.dumps(_normalize_keywords(keywords))
    if k:
        k.name = name
        k.description = description
        k.body = body
        k.keywords = keywords_json
        k.disable = disable
        k.updated_at = _utcnow()
    else:
        k = Kpatch(
            scope=scope.scope,
            org_id=scope.org_id,
            project_slug=scope.project_slug,
            user_id=scope.user_id,
            slug=slug,
            disable=disable,
            name=name,
            description=description,
            body=body,
            keywords=keywords_json,
        )
        session.add(k)
    await session.commit()
    await session.refresh(k)
    return serialize_kpatch(k)


async def set_disable(
    session: AsyncSession, scope: Scope, slug: str, disable: bool
) -> dict:
    """Toggle the disable flag, creating a stub row at the scope if needed.

    Used by the project/member views to "disable an inherited kpatch" with
    a single mutation: if no row exists at the target scope, create one
    with the matching slug, an empty body, and ``disable=disable``.
    """
    if scope.scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail="invalid scope")
    q = _scope_filter(select(Kpatch), scope).where(Kpatch.slug == slug)
    result = await session.exec(q)
    k = result.first()
    if k:
        k.disable = disable
        k.updated_at = _utcnow()
    else:
        if not SLUG_RE.match(slug):
            raise HTTPException(status_code=400, detail="invalid kpatch slug")
        k = Kpatch(
            scope=scope.scope,
            org_id=scope.org_id,
            project_slug=scope.project_slug,
            user_id=scope.user_id,
            slug=slug,
            disable=disable,
            name=slug,  # minimal stub; user can edit later if it becomes an override
            description=None,
            body="",
            keywords="[]",
        )
        session.add(k)
    await session.commit()
    await session.refresh(k)
    return serialize_kpatch(k)


async def delete_kpatch(
    session: AsyncSession, scope: Scope, slug: str
) -> None:
    k = await get_kpatch(session, scope, slug)
    triggers = await session.exec(
        select(Trigger).where(Trigger.kpatch_id == k.pk_id)
    )
    for t in triggers.all():
        await session.delete(t)
    await session.delete(k)
    await session.commit()


# ---- Inherited-view helpers ----------------------------------------------

async def list_with_inherited(
    session: AsyncSession, scope: Scope
) -> list[dict]:
    """List kpatches at `scope` plus inherited rows from higher scopes.

    Each returned dict carries an ``origin_scope`` (the scope the row was
    fetched at) and a ``shadowed_at_current`` flag indicating whether a
    sibling row already exists at ``scope`` for that slug.
    """
    await _ensure_org(session, scope.org_id)

    # Build the list of scope tuples to fetch in priority order
    # (lowest first). The first scope is `scope` itself; subsequent
    # scopes are those *higher* than it.
    scopes_to_fetch: list[Scope] = [scope]
    if scope.scope == SCOPE_MEMBER:
        scopes_to_fetch.append(
            Scope.project(scope.org_id, scope.project_slug)
        )
    if scope.scope in (SCOPE_MEMBER, SCOPE_PROJECT):
        scopes_to_fetch.append(Scope.org(scope.org_id))

    own: dict[str, Kpatch] = {}
    inherited: list[tuple[Scope, Kpatch]] = []
    own_slugs: set[str] = set()

    # Own scope rows first.
    own_result = await session.exec(_scope_filter(select(Kpatch), scope))
    for k in own_result.all():
        own[k.slug] = k
        own_slugs.add(k.slug)

    # Higher scopes — collect, mark whether shadowed.
    for higher in scopes_to_fetch[1:]:
        result = await session.exec(_scope_filter(select(Kpatch), higher))
        for k in result.all():
            inherited.append((higher, k))

    out: list[dict] = []
    for k in own.values():
        row = serialize_kpatch(k)
        row["origin_scope"] = k.scope
        row["shadowed_at_current"] = False
        out.append(row)
    for src, k in inherited:
        row = serialize_kpatch(k)
        row["origin_scope"] = src.scope
        row["shadowed_at_current"] = k.slug in own_slugs
        out.append(row)
    # Stable order: by slug, then own first.
    out.sort(key=lambda r: (r["slug"], 0 if r["origin_scope"] == scope.scope else 1))
    return out
