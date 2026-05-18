from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    slug: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)


class Skill(SQLModel, table=True):
    __tablename__ = "skills"

    project_slug: str = Field(primary_key=True, foreign_key="projects.slug")
    id: str = Field(primary_key=True)
    name: str
    description: Optional[str] = None
    body: str
    # Stored as JSON-encoded TEXT to keep schema portable across SQLite & Postgres.
    keywords: str = Field(default="[]")


class Rule(SQLModel, table=True):
    __tablename__ = "rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_slug: str = Field(foreign_key="projects.slug", index=True)
    on_event: str = Field(index=True)
    match: Optional[str] = None
    # JSON-encoded array of skill ids.
    inject: str = Field(default="[]")
    once_per_session: bool = Field(default=False)


class SessionDedupe(SQLModel, table=True):
    __tablename__ = "session_dedupe"

    session_id: str = Field(primary_key=True)
    rule_id: int = Field(primary_key=True, foreign_key="rules.id")
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
