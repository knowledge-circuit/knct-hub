"""Scope-based kpatch resolution.

For a hook on (caller_org, project_slug, caller_user_id):
  1. Fetch every kpatch at scope=org AND org_id=caller_org
  2. Fetch every kpatch at scope=project AND org_id=caller_org AND project_slug=project_slug
  3. Fetch every kpatch at scope=member AND org_id=caller_org AND project_slug=project_slug AND user_id=caller_user_id
  4. Group by slug, winner = lowest-scope row (member > project > org)
  5. Drop winners with disable=true
  6. Return survivors and their triggers

No bundles. No layered arrays. The fact that a lower-scope row shadows
a higher-scope one *is* the override / disable mechanism.
"""


import json
from dataclasses import dataclass

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import (
    NOT_APPLICABLE,
    SCOPE_MEMBER,
    SCOPE_ORG,
    SCOPE_PROJECT,
    Kpatch,
    Trigger,
)


@dataclass
class EffectiveKpatch:
    pk_id: int
    slug: str
    origin_scope: str
    name: str
    description: str | None
    body: str
    keywords: list[str]
    triggers: list[Trigger]


_SCOPE_PRIORITY = {SCOPE_MEMBER: 0, SCOPE_PROJECT: 1, SCOPE_ORG: 2}


async def resolve_effective_kpatches(
    session: AsyncSession,
    *,
    org_id: str,
    project_slug: str,
    user_id: str,
) -> list[EffectiveKpatch]:
    # Collect candidate rows from the three scopes in one query each.
    org_rows = (
        await session.exec(
            select(Kpatch).where(
                Kpatch.scope == SCOPE_ORG,
                Kpatch.org_id == org_id,
                Kpatch.project_slug == NOT_APPLICABLE,
                Kpatch.user_id == NOT_APPLICABLE,
            )
        )
    ).all()
    project_rows = (
        await session.exec(
            select(Kpatch).where(
                Kpatch.scope == SCOPE_PROJECT,
                Kpatch.org_id == org_id,
                Kpatch.project_slug == project_slug,
                Kpatch.user_id == NOT_APPLICABLE,
            )
        )
    ).all()
    member_rows = (
        await session.exec(
            select(Kpatch).where(
                Kpatch.scope == SCOPE_MEMBER,
                Kpatch.org_id == org_id,
                Kpatch.project_slug == project_slug,
                Kpatch.user_id == user_id,
            )
        )
    ).all()

    # Pick lowest-scope winner per slug.
    winners: dict[str, Kpatch] = {}
    for k in list(org_rows) + list(project_rows) + list(member_rows):
        cur = winners.get(k.slug)
        if cur is None or _SCOPE_PRIORITY[k.scope] < _SCOPE_PRIORITY[cur.scope]:
            winners[k.slug] = k

    # Drop disabled winners.
    survivors = [k for k in winners.values() if not k.disable]
    if not survivors:
        return []

    # Load triggers in one shot for the surviving pk_ids.
    pk_ids = [k.pk_id for k in survivors if k.pk_id is not None]
    triggers_by_kpatch: dict[int, list[Trigger]] = {}
    if pk_ids:
        result = await session.exec(
            select(Trigger).where(Trigger.kpatch_id.in_(pk_ids))
        )
        for t in result.all():
            triggers_by_kpatch.setdefault(t.kpatch_id, []).append(t)

    # Deterministic order: by slug.
    survivors.sort(key=lambda k: k.slug)
    return [
        EffectiveKpatch(
            pk_id=k.pk_id,
            slug=k.slug,
            origin_scope=k.scope,
            name=k.name,
            description=k.description,
            body=k.body,
            keywords=json.loads(k.keywords or "[]"),
            triggers=triggers_by_kpatch.get(k.pk_id, []),
        )
        for k in survivors
    ]
