"""Parse markdown-with-frontmatter and create a kpatch at a given scope.

Scope is chosen by the caller (which endpoint they POSTed to). The
markdown file itself carries no scope hint.
"""


import json
from dataclasses import dataclass
from typing import Any, Optional

import yaml
from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from knct_hub.db.models import Trigger
from knct_hub.services.kpatches import Scope, upsert_kpatch
from knct_hub.services.triggers import VALID_EVENTS, create_trigger


@dataclass
class ParsedKpatch:
    slug: str
    name: str
    description: Optional[str]
    keywords: list[str]
    body: str
    trigger: Optional[dict]


def _split_frontmatter(text: str) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise HTTPException(status_code=400, detail="missing frontmatter")
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        raise HTTPException(status_code=400, detail="unterminated frontmatter")
    fm = "".join(lines[1:end_idx])
    body = "".join(lines[end_idx + 1:])
    return fm, body.lstrip("\n")


def _normalize_keywords(raw: Any) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise HTTPException(status_code=400, detail="keywords must be a list")
    out: list[str] = []
    seen: set[str] = set()
    for v in raw:
        if not isinstance(v, str):
            continue
        v = v.strip()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def _validate_trigger(raw: Any) -> Optional[dict]:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="trigger must be a mapping")
    event = raw.get("event")
    if event not in VALID_EVENTS:
        raise HTTPException(status_code=400, detail="trigger.event invalid")
    pc = raw.get("prompt_contains")
    if pc is not None and (
        not isinstance(pc, list) or not all(isinstance(s, str) for s in pc)
    ):
        raise HTTPException(
            status_code=400,
            detail="trigger.prompt_contains must be a list of strings",
        )
    pm = raw.get("path_match")
    if pm is not None and not isinstance(pm, str):
        raise HTTPException(status_code=400, detail="trigger.path_match must be a string")
    once = raw.get("once_per_session")
    if once is not None and not isinstance(once, bool):
        raise HTTPException(status_code=400, detail="trigger.once_per_session must be a bool")
    return {
        "event": event,
        "prompt_contains": pc,
        "path_match": pm,
        "once_per_session": once,
    }


def parse_kpatch(text: str) -> ParsedKpatch:
    fm_text, body = _split_frontmatter(text)
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"invalid YAML frontmatter: {e}")
    if not isinstance(fm, dict):
        raise HTTPException(status_code=400, detail="frontmatter must be a mapping")

    slug = (fm.get("id") or "").strip() if isinstance(fm.get("id"), str) else ""
    name = (fm.get("name") or "").strip() if isinstance(fm.get("name"), str) else ""
    if not slug:
        raise HTTPException(status_code=400, detail="missing id")
    if not name:
        raise HTTPException(status_code=400, detail="missing name")
    description = fm.get("description")
    if description is not None and not isinstance(description, str):
        raise HTTPException(status_code=400, detail="description must be a string")
    return ParsedKpatch(
        slug=slug,
        name=name,
        description=description,
        keywords=_normalize_keywords(fm.get("keywords")),
        body=body,
        trigger=_validate_trigger(fm.get("trigger")),
    )


def _trigger_matches(t: Trigger, trig: dict) -> bool:
    same_event = t.event == trig["event"]
    same_path = (t.path_match or None) == (trig.get("path_match") or None)
    existing = json.loads(t.prompt_contains) if t.prompt_contains else None
    target = trig.get("prompt_contains")
    return same_event and same_path and existing == target


async def import_kpatch_file(
    session: AsyncSession, scope: Scope, text: str
) -> dict:
    parsed = parse_kpatch(text)
    saved = await upsert_kpatch(
        session,
        scope,
        parsed.slug,
        name=parsed.name,
        description=parsed.description,
        body=parsed.body,
        keywords=parsed.keywords,
    )
    created_trigger: Optional[dict] = None
    if parsed.trigger is not None:
        result = await session.exec(
            select(Trigger).where(Trigger.kpatch_id == saved["pk_id"])
        )
        existing = list(result.all())
        if not any(_trigger_matches(t, parsed.trigger) for t in existing):
            created_trigger = await create_trigger(
                session,
                saved["pk_id"],
                event=parsed.trigger["event"],
                prompt_contains=parsed.trigger.get("prompt_contains"),
                path_match=parsed.trigger.get("path_match"),
                once_per_session=parsed.trigger.get("once_per_session"),
            )
    return {"kpatch": saved, "trigger": created_trigger}
