"""Bundle inheritance resolver.

Flattens community → org → project bundles for a hook request, applies
the project's `disabled_kpatch_ids` and `overridden_kpatches`, and yields
the effective list of (kpatch, [triggers]) pairs that the trigger
evaluator should consider.

The "three layers" framing in the spec collapses for an already-imported
community bundle (community-library import deep-copies into the target
org) — at resolution time those bundles are indistinguishable from
org-owned bundles. The shape stays generic: any ordered list of bundles
attached at the org or project level feeds in here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import Bundle, Kpatch, Org, Project, Trigger


@dataclass
class EffectiveKpatch:
    org_id: str
    id: str
    name: str
    description: str | None
    body: str
    keywords: list[str]
    triggers: list[Trigger]


def _bundles_in_order(org: Org, project: Project) -> list[str]:
    org_defaults = json.loads(org.default_bundles or "[]")
    project_attached = json.loads(project.attached_bundles or "[]")
    seen: set[str] = set()
    out: list[str] = []
    for b in (*org_defaults, *project_attached):
        if b and b not in seen:
            seen.add(b)
            out.append(b)
    return out


async def _load_bundles(
    session: AsyncSession, org_id: str, ids: list[str]
) -> list[Bundle]:
    if not ids:
        return []
    result = await session.exec(
        select(Bundle).where(Bundle.org_id == org_id, Bundle.id.in_(ids))
    )
    found = {b.id: b for b in result.all()}
    return [found[i] for i in ids if i in found]


async def _load_kpatches(
    session: AsyncSession, org_id: str, ids: list[str]
) -> dict[str, Kpatch]:
    if not ids:
        return {}
    result = await session.exec(
        select(Kpatch).where(Kpatch.org_id == org_id, Kpatch.id.in_(ids))
    )
    return {k.id: k for k in result.all()}


async def _load_triggers(
    session: AsyncSession, org_id: str, kpatch_ids: Iterable[str]
) -> dict[str, list[Trigger]]:
    ids = list(kpatch_ids)
    if not ids:
        return {}
    result = await session.exec(
        select(Trigger).where(
            Trigger.kpatch_org_id == org_id, Trigger.kpatch_id.in_(ids)
        )
    )
    grouped: dict[str, list[Trigger]] = {}
    for t in result.all():
        grouped.setdefault(t.kpatch_id, []).append(t)
    return grouped


def _override_to_kpatch(
    override: dict, org_id: str
) -> tuple[Kpatch, list[Trigger]]:
    """Materialize a project-level override into Kpatch + Trigger objects.

    Override shape (stored as JSON in project.overridden_kpatches):
        {
          "id": "commit-conventions",
          "name": "...",
          "description": "...",
          "body": "...",
          "keywords": ["..."],
          "triggers": [
            {"event": "user_prompt", "prompt_contains": ["commit"],
             "path_match": null, "once_per_session": false}
          ]
        }
    """
    kpatch = Kpatch(
        org_id=org_id,
        id=override["id"],
        name=override.get("name", override["id"]),
        description=override.get("description"),
        body=override.get("body", ""),
        keywords=json.dumps(override.get("keywords", [])),
    )
    triggers: list[Trigger] = []
    for t in override.get("triggers", []) or []:
        triggers.append(
            Trigger(
                id=None,
                kpatch_org_id=org_id,
                kpatch_id=override["id"],
                event=t["event"],
                prompt_contains=(
                    json.dumps(t["prompt_contains"])
                    if t.get("prompt_contains")
                    else None
                ),
                path_match=t.get("path_match"),
                once_per_session=bool(t.get("once_per_session", False)),
            )
        )
    return kpatch, triggers


async def resolve_effective_kpatches(
    session: AsyncSession, org: Org, project: Project
) -> list[EffectiveKpatch]:
    bundle_ids = _bundles_in_order(org, project)
    bundles = await _load_bundles(session, org.id, bundle_ids)

    # Flatten ordered kpatch ids across bundles, dedupe first-occurrence.
    ordered_kpatch_ids: list[str] = []
    seen_kpatch: set[str] = set()
    for b in bundles:
        for kid in json.loads(b.kpatch_ids or "[]"):
            if kid not in seen_kpatch:
                seen_kpatch.add(kid)
                ordered_kpatch_ids.append(kid)

    # Escape hatch: also include any kpatches in the org that aren't in
    # an attached bundle. Appended after bundle-derived ids; order within
    # this group is by kpatch id for determinism.
    if org.include_unbundled:
        all_in_org = await session.exec(
            select(Kpatch.id).where(Kpatch.org_id == org.id).order_by(Kpatch.id)
        )
        for kid in all_in_org.all():
            if kid not in seen_kpatch:
                seen_kpatch.add(kid)
                ordered_kpatch_ids.append(kid)

    # Apply project-level disable.
    disabled = set(json.loads(project.disabled_kpatch_ids or "[]"))
    ordered_kpatch_ids = [k for k in ordered_kpatch_ids if k not in disabled]

    # Apply project-level overrides: replace matching ids entirely.
    overrides_raw = json.loads(project.overridden_kpatches or "[]")
    overrides_by_id: dict[str, tuple[Kpatch, list[Trigger]]] = {}
    for ov in overrides_raw:
        try:
            overrides_by_id[ov["id"]] = _override_to_kpatch(ov, org.id)
        except (KeyError, TypeError):
            continue  # malformed override silently ignored

    # Make sure overrides whose id isn't already inherited still get to
    # contribute (spec: project-level redefinition wins; "matching an
    # inherited id" is the common case but appending a fresh one is also
    # legitimate project-level content).
    for oid in overrides_by_id:
        if oid not in ordered_kpatch_ids:
            ordered_kpatch_ids.append(oid)

    # Load inherited kpatches + their triggers in one round-trip each.
    inherited_ids = [
        k for k in ordered_kpatch_ids if k not in overrides_by_id
    ]
    inherited_kpatches = await _load_kpatches(session, org.id, inherited_ids)
    inherited_triggers = await _load_triggers(session, org.id, inherited_ids)

    effective: list[EffectiveKpatch] = []
    for kid in ordered_kpatch_ids:
        if kid in overrides_by_id:
            k, triggers = overrides_by_id[kid]
        else:
            k = inherited_kpatches.get(kid)
            if k is None:
                continue  # bundle referenced a missing kpatch — skip
            triggers = inherited_triggers.get(kid, [])
        effective.append(
            EffectiveKpatch(
                org_id=k.org_id,
                id=k.id,
                name=k.name,
                description=k.description,
                body=k.body,
                keywords=json.loads(k.keywords or "[]"),
                triggers=triggers,
            )
        )
    return effective
