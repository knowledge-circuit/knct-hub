from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Scope sentinels used in the unique key on `kpatches`.
SCOPE_ORG = "org"
SCOPE_PROJECT = "project"
SCOPE_MEMBER = "member"
NOT_APPLICABLE = ""  # used for project_slug / user_id when not in scope


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    clerk_id: Optional[str] = Field(default=None, unique=True, index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class Org(SQLModel, table=True):
    __tablename__ = "orgs"

    id: str = Field(primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=_utcnow)


class OrgMember(SQLModel, table=True):
    __tablename__ = "org_members"

    org_id: str = Field(primary_key=True, foreign_key="orgs.id")
    user_id: str = Field(primary_key=True, foreign_key="users.id")
    role: str = Field(default="member")  # owner | admin | member
    created_at: datetime = Field(default_factory=_utcnow)


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    org_id: str = Field(primary_key=True, foreign_key="orgs.id")
    slug: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)
    access_mode: str = Field(default="org")  # "org" | "invite_only"
    members: str = Field(default="[]")  # JSON list of user ids


class Kpatch(SQLModel, table=True):
    __tablename__ = "kpatches"

    pk_id: Optional[int] = Field(default=None, primary_key=True)
    scope: str = Field(default=SCOPE_ORG)  # org | project | member
    org_id: str = Field(foreign_key="orgs.id", index=True)
    # Empty string when not applicable to the scope.
    project_slug: str = Field(default=NOT_APPLICABLE, index=True)
    user_id: str = Field(default=NOT_APPLICABLE, index=True)
    slug: str
    disable: bool = Field(default=False)
    name: str
    description: Optional[str] = None
    body: str = ""
    keywords: str = Field(default="[]")  # JSON
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Trigger(SQLModel, table=True):
    __tablename__ = "triggers"

    id: Optional[int] = Field(default=None, primary_key=True)
    kpatch_id: int = Field(foreign_key="kpatches.pk_id", index=True)
    event: str = Field(index=True)  # session_start | user_prompt | pre_tool_use
    prompt_contains: Optional[str] = None  # JSON list or null
    path_match: Optional[str] = None
    once_per_session: bool = Field(default=False)


class DeviceToken(SQLModel, table=True):
    __tablename__ = "device_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class SessionDedupe(SQLModel, table=True):
    __tablename__ = "session_dedupe"

    session_id: str = Field(primary_key=True)
    trigger_id: int = Field(primary_key=True, foreign_key="triggers.id")
    fired_at: datetime = Field(default_factory=_utcnow)


class Trace(SQLModel, table=True):
    __tablename__ = "traces"

    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=_utcnow, index=True)
    event: str
    session_id: Optional[str] = None
    cwd: Optional[str] = None
    tool_name: Optional[str] = None
    payload: str
    response: Optional[str] = None
    kpatch_ids: Optional[str] = None
    triggered_by: Optional[str] = None
    project_org_id: Optional[str] = Field(default=None, index=True)
    project_slug: Optional[str] = Field(default=None, index=True)
