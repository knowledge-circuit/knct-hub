import json
import re
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import Bundle, Kpatch, Org

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)

COMMUNITY_ORG = "community"


def serialize_bundle(b: Bundle) -> dict:
    return {
        "id": b.id,
        "org_id": b.org_id,
        "name": b.name,
        "version": b.version,
        "kpatch_ids": json.loads(b.kpatch_ids or "[]"),
        "created_at": b.created_at.isoformat(),
        "updated_at": b.updated_at.isoformat(),
    }


def _parse_semver(v: str) -> tuple[int, int, int]:
    m = SEMVER_RE.match(v)
    if not m:
        raise HTTPException(status_code=400, detail="invalid semver")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _semver_gt(new: str, old: str) -> bool:
    # Compare only major.minor.patch for monotonicity.
    return _parse_semver(new) > _parse_semver(old)


async def _ensure_org(session: AsyncSession, org_id: str) -> None:
    result = await session.exec(select(Org).where(Org.id == org_id))
    if not result.first():
        raise HTTPException(status_code=404, detail="org not found")


async def _validate_kpatch_refs(
    session: AsyncSession, org_id: str, kpatch_ids: list[str]
) -> None:
    if not kpatch_ids:
        return
    # Community bundles are allowed to reference kpatches owned by the
    # community org regardless of the bundle's org; for other orgs the
    # refs must match the bundle's org.
    allowed_orgs = {org_id}
    if org_id == COMMUNITY_ORG:
        allowed_orgs.add(COMMUNITY_ORG)
    result = await session.exec(
        select(Kpatch).where(Kpatch.id.in_(kpatch_ids))
    )
    found = {(k.org_id, k.id) for k in result.all()}
    missing: list[str] = []
    for kid in kpatch_ids:
        if not any(o in allowed_orgs and (o, kid) in found for o in allowed_orgs):
            missing.append(kid)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"kpatch_ids not found in org '{org_id}': {missing}",
        )


async def list_bundles(session: AsyncSession, org_id: str) -> list[dict]:
    await _ensure_org(session, org_id)
    result = await session.exec(
        select(Bundle).where(Bundle.org_id == org_id).order_by(Bundle.id)
    )
    return [serialize_bundle(b) for b in result.all()]


async def get_bundle(
    session: AsyncSession, org_id: str, bundle_id: str
) -> Bundle:
    result = await session.exec(
        select(Bundle).where(Bundle.org_id == org_id, Bundle.id == bundle_id)
    )
    b = result.first()
    if not b:
        raise HTTPException(status_code=404, detail="bundle not found")
    return b


async def upsert_bundle(
    session: AsyncSession,
    org_id: str,
    bundle_id: str,
    *,
    name: str,
    version: str,
    kpatch_ids: list[str],
) -> dict:
    if not SLUG_RE.match(bundle_id):
        raise HTTPException(status_code=400, detail="invalid bundle id")
    _parse_semver(version)  # validate format
    await _ensure_org(session, org_id)
    await _validate_kpatch_refs(session, org_id, kpatch_ids)

    result = await session.exec(
        select(Bundle).where(Bundle.org_id == org_id, Bundle.id == bundle_id)
    )
    existing = result.first()
    now = datetime.now(timezone.utc)
    if existing:
        if not _semver_gt(version, existing.version):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"version {version} not greater than current "
                    f"{existing.version}"
                ),
            )
        existing.name = name
        existing.version = version
        existing.kpatch_ids = json.dumps(kpatch_ids)
        existing.updated_at = now
        bundle = existing
    else:
        bundle = Bundle(
            org_id=org_id,
            id=bundle_id,
            name=name,
            version=version,
            kpatch_ids=json.dumps(kpatch_ids),
        )
        session.add(bundle)
    await session.commit()
    await session.refresh(bundle)
    return serialize_bundle(bundle)


async def delete_bundle(
    session: AsyncSession, org_id: str, bundle_id: str
) -> None:
    bundle = await get_bundle(session, org_id, bundle_id)
    await session.delete(bundle)
    await session.commit()
