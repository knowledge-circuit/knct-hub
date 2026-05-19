from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
    # JSON-encoded ordered list of bundle ids.
    default_bundles: str = Field(default="[]")
    # When true, the resolver also injects kpatches in this org that are
    # not part of any attached bundle. Escape hatch for solo/small-team use
    # where the bundle layer is overhead.
    include_unbundled: bool = Field(default=False)


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
    # JSON-encoded arrays.
    members: str = Field(default="[]")
    attached_bundles: str = Field(default="[]")
    disabled_kpatch_ids: str = Field(default="[]")
    overridden_kpatches: str = Field(default="[]")


class Kpatch(SQLModel, table=True):
    __tablename__ = "kpatches"

    org_id: str = Field(primary_key=True, foreign_key="orgs.id")
    id: str = Field(primary_key=True)
    name: str
    description: Optional[str] = None
    body: str
    keywords: str = Field(default="[]")  # JSON
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Trigger(SQLModel, table=True):
    __tablename__ = "triggers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["kpatch_org_id", "kpatch_id"],
            ["kpatches.org_id", "kpatches.id"],
            ondelete="CASCADE",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    kpatch_org_id: str = Field(index=True)
    kpatch_id: str = Field(index=True)
    event: str = Field(index=True)  # session_start | user_prompt | pre_tool_use
    # JSON-encoded array of strings; only meaningful for event=user_prompt.
    prompt_contains: Optional[str] = Field(default=None)
    path_match: Optional[str] = Field(default=None)
    once_per_session: bool = Field(default=False)


class Bundle(SQLModel, table=True):
    __tablename__ = "bundles"

    org_id: str = Field(primary_key=True, foreign_key="orgs.id")
    id: str = Field(primary_key=True)
    name: str
    version: str  # semver string
    kpatch_ids: str = Field(default="[]")  # JSON ordered list
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


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
    payload: str  # JSON text
    response: Optional[str] = None  # JSON text
    # Which kpatches contributed to the response (JSON list of ids).
    # Null when no injection occurred or for non-injection events.
    kpatch_ids: Optional[str] = None
    # Which trigger rows matched (JSON list of ints).
    triggered_by: Optional[str] = None
    # Owning project for fast filtering. Composite (org_id, slug).
    project_org_id: Optional[str] = Field(default=None, index=True)
    project_slug: Optional[str] = Field(default=None, index=True)
