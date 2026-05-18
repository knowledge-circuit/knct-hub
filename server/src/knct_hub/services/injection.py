import json

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import func, select

from knct_hub.db.models import Rule, Skill
from knct_hub.services.engine import clear_dedupe, evaluate


def inject_response(event_name: str, markdown: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": markdown,
        }
    }


def _concat(bodies: list[str]) -> str:
    return "\n\n---\n\n".join(bodies)


async def _fetch_skill_bodies(
    session: AsyncSession, slug: str, ids: list[str]
) -> list[str]:
    if not ids:
        return []
    result = await session.exec(
        select(Skill).where(Skill.project_slug == slug, Skill.id.in_(ids))
    )
    by_id = {s.id: s.body for s in result.all()}
    return [by_id[i] for i in ids if i in by_id]


async def handle_session_start(
    session: AsyncSession, slug: str, payload: dict
) -> dict:
    skills_result = await session.exec(
        select(Skill).where(Skill.project_slug == slug).order_by(Skill.id)
    )
    skills = list(skills_result.all())
    rule_count_result = await session.exec(
        select(func.count(Rule.id)).where(Rule.project_slug == slug)
    )
    rule_count = rule_count_result.first() or 0

    if not skills and not rule_count:
        return {}

    lines = [f"This project has {len(skills)} skills and {rule_count} rules."]
    if skills:
        lines.append("")
        for s in skills:
            desc = s.description or ""
            lines.append(f"- **{s.name}** (`{s.id}`): {desc}")
    return inject_response("SessionStart", "\n".join(lines))


async def handle_prompt_submit(
    session: AsyncSession, slug: str, payload: dict
) -> dict:
    prompt = (payload.get("prompt") or "").lower()
    if not prompt:
        return {}
    result = await session.exec(select(Skill).where(Skill.project_slug == slug))
    matched_bodies: list[str] = []
    for skill in result.all():
        keywords = json.loads(skill.keywords or "[]")
        if any(k and k.lower() in prompt for k in keywords):
            matched_bodies.append(skill.body)
    if not matched_bodies:
        return {}
    return inject_response("UserPromptSubmit", _concat(matched_bodies))


async def handle_pre_tool(session: AsyncSession, slug: str, payload: dict) -> dict:
    tool = payload.get("tool_name") or (payload.get("tool_input") or {}).get("tool_name")
    if tool in ("Edit", "Write"):
        on_event = "pre_edit"
    elif tool == "Read":
        on_event = "pre_read"
    else:
        return {}
    skill_ids = await evaluate(session, slug, on_event, payload)
    if not skill_ids:
        return {}
    bodies = await _fetch_skill_bodies(session, slug, skill_ids)
    if not bodies:
        return {}
    return inject_response("PreToolUse", _concat(bodies))


async def handle_post_compact(
    session: AsyncSession, slug: str, payload: dict
) -> dict:
    sid = payload.get("session_id")
    if sid:
        await clear_dedupe(session, sid)
    return {}
