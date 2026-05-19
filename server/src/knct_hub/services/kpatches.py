import json
import re
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import Kpatch, Org, Trigger

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def serialize_kpatch(k: Kpatch) -> dict:
    return {
        "id": k.id,
        "org_id": k.org_id,
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


async def list_kpatches(session: AsyncSession, org_id: str) -> list[dict]:
    await _ensure_org(session, org_id)
    result = await session.exec(
        select(Kpatch).where(Kpatch.org_id == org_id).order_by(Kpatch.id)
    )
    return [serialize_kpatch(k) for k in result.all()]


async def get_kpatch(
    session: AsyncSession, org_id: str, kpatch_id: str
) -> Kpatch:
    result = await session.exec(
        select(Kpatch).where(Kpatch.org_id == org_id, Kpatch.id == kpatch_id)
    )
    k = result.first()
    if not k:
        raise HTTPException(status_code=404, detail="kpatch not found")
    return k


async def upsert_kpatch(
    session: AsyncSession,
    org_id: str,
    kpatch_id: str,
    *,
    name: str,
    description: str | None,
    body: str,
    keywords: list[str],
) -> dict:
    if not SLUG_RE.match(kpatch_id):
        raise HTTPException(status_code=400, detail="invalid kpatch id")
    await _ensure_org(session, org_id)
    result = await session.exec(
        select(Kpatch).where(Kpatch.org_id == org_id, Kpatch.id == kpatch_id)
    )
    k = result.first()
    keywords_json = json.dumps(_normalize_keywords(keywords))
    if k:
        k.name = name
        k.description = description
        k.body = body
        k.keywords = keywords_json
        k.updated_at = _utcnow()
    else:
        k = Kpatch(
            org_id=org_id,
            id=kpatch_id,
            name=name,
            description=description,
            body=body,
            keywords=keywords_json,
        )
        session.add(k)
    await session.commit()
    await session.refresh(k)
    return serialize_kpatch(k)


async def delete_kpatch(
    session: AsyncSession, org_id: str, kpatch_id: str
) -> None:
    k = await get_kpatch(session, org_id, kpatch_id)
    # Cascade trigger deletion explicitly (SQLite enforces FK only when PRAGMA on).
    triggers = await session.exec(
        select(Trigger).where(
            Trigger.kpatch_org_id == org_id, Trigger.kpatch_id == kpatch_id
        )
    )
    for t in triggers.all():
        await session.delete(t)
    await session.delete(k)
    await session.commit()
