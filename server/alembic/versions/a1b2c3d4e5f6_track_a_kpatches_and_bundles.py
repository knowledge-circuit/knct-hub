"""track_a_kpatches_and_bundles

Adds orgs, org_members, users, kpatches, triggers, bundles, device_tokens.
Extends projects with org_id, access_mode, members, attached_bundles,
disabled_kpatch_ids, overridden_kpatches; the PK becomes (org_id, slug).
Drops rules and skills tables (a JSON snapshot is written under the
knct data dir before the drop). Recreates session_dedupe keyed on
trigger_id instead of rule_id; any pre-existing dedupe rows are
discarded because rules data is not migrated forward.

Revision ID: a1b2c3d4e5f6
Revises: 75bba1382501
Create Date: 2026-05-19 00:00:00.000000

"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "75bba1382501"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _snapshot_legacy_rows() -> None:
    """Dump existing rules/skills rows to JSON before dropping the tables.

    Snapshot path: $KNCT_MIGRATION_SNAPSHOT_DIR/track-a-{revision}.json,
    falling back to ~/.knct/. Skips silently if both tables are empty.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    rules: list[dict] = []
    skills: list[dict] = []
    if "rules" in existing:
        rules = [dict(r._mapping) for r in bind.execute(sa.text("SELECT * FROM rules"))]
    if "skills" in existing:
        skills = [dict(r._mapping) for r in bind.execute(sa.text("SELECT * FROM skills"))]

    if not rules and not skills:
        return

    snapshot_dir = Path(
        os.environ.get("KNCT_MIGRATION_SNAPSHOT_DIR", str(Path.home() / ".knct"))
    )
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    out = snapshot_dir / f"track-a-{revision}.json"
    out.write_text(
        json.dumps({"rules": rules, "skills": skills}, default=str, indent=2)
    )


def upgrade() -> None:
    # 1. New independent tables (FK targets first).
    op.create_table(
        "users",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("clerk_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clerk_id"),
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_index("ix_users_clerk_id", ["clerk_id"], unique=False)

    op.create_table(
        "orgs",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("default_bundles", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="[]"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "org_members",
        sa.Column("org_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("role", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["orgs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("org_id", "user_id"),
    )

    # 2. Seed a 'solo' org + user so existing projects can FK to a valid org.
    #    Runtime solo-mode bootstrap (see solo-mode capability) tolerates this
    #    row already existing.
    now_sql = sa.text(
        "CURRENT_TIMESTAMP" if op.get_bind().dialect.name != "sqlite" else "CURRENT_TIMESTAMP"
    )
    op.execute(
        sa.text(
            "INSERT INTO users (id, clerk_id, created_at) "
            "VALUES ('solo', NULL, CURRENT_TIMESTAMP)"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO orgs (id, name, created_at, default_bundles) "
            "VALUES ('solo', 'Solo', CURRENT_TIMESTAMP, '[]')"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO org_members (org_id, user_id, role, created_at) "
            "VALUES ('solo', 'solo', 'owner', CURRENT_TIMESTAMP)"
        )
    )

    # 3. Extend projects: new columns + composite PK (org_id, slug).
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column(
                "org_id",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default="solo",
            )
        )
        batch_op.add_column(
            sa.Column(
                "access_mode",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default="org",
            )
        )
        batch_op.add_column(
            sa.Column(
                "members",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default="[]",
            )
        )
        batch_op.add_column(
            sa.Column(
                "attached_bundles",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default="[]",
            )
        )
        batch_op.add_column(
            sa.Column(
                "disabled_kpatch_ids",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default="[]",
            )
        )
        batch_op.add_column(
            sa.Column(
                "overridden_kpatches",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default="[]",
            )
        )
        batch_op.create_foreign_key(
            "fk_projects_org_id_orgs", "orgs", ["org_id"], ["id"]
        )
        # SQLite via batch mode recreates the table; we get a fresh PK below.
        # Drop the old single-column PK before re-adding (batch mode handles this).

    # Replace PK to (org_id, slug). batch_alter_table can recreate the PK on
    # SQLite; on Postgres we drop and re-add explicitly.
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("projects") as batch_op:
            batch_op.create_primary_key("pk_projects", ["org_id", "slug"])
    else:
        op.drop_constraint("projects_pkey", "projects", type_="primary")
        op.create_primary_key("pk_projects", "projects", ["org_id", "slug"])

    # 4. Snapshot then drop legacy rules + skills + session_dedupe.
    _snapshot_legacy_rows()

    # session_dedupe FKs rules, drop first.
    op.drop_table("session_dedupe")

    inspector = sa.inspect(op.get_bind())
    rule_indexes = {idx["name"] for idx in inspector.get_indexes("rules")}
    with op.batch_alter_table("rules") as batch_op:
        if "ix_rules_on_event" in rule_indexes:
            batch_op.drop_index("ix_rules_on_event")
        if "ix_rules_project_slug" in rule_indexes:
            batch_op.drop_index("ix_rules_project_slug")
    op.drop_table("rules")
    op.drop_table("skills")

    # 5. New core tables: kpatches, triggers, bundles, device_tokens.
    op.create_table(
        "kpatches",
        sa.Column("org_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("body", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("keywords", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["orgs.id"]),
        sa.PrimaryKeyConstraint("org_id", "id"),
    )

    op.create_table(
        "triggers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kpatch_org_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("kpatch_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("event", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("prompt_contains", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("path_match", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("once_per_session", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(
            ["kpatch_org_id", "kpatch_id"],
            ["kpatches.org_id", "kpatches.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("triggers") as batch_op:
        batch_op.create_index("ix_triggers_event", ["event"], unique=False)
        batch_op.create_index(
            "ix_triggers_kpatch", ["kpatch_org_id", "kpatch_id"], unique=False
        )

    op.create_table(
        "bundles",
        sa.Column("org_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("kpatch_ids", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["orgs.id"]),
        sa.PrimaryKeyConstraint("org_id", "id"),
    )

    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("token_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    with op.batch_alter_table("device_tokens") as batch_op:
        batch_op.create_index("ix_device_tokens_user_id", ["user_id"], unique=False)
        batch_op.create_index(
            "ix_device_tokens_token_hash", ["token_hash"], unique=False
        )

    # 6. Recreate session_dedupe keyed on trigger_id (fresh; no legacy data).
    op.create_table(
        "session_dedupe",
        sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("trigger_id", sa.Integer(), nullable=False),
        sa.Column("fired_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["trigger_id"], ["triggers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id", "trigger_id"),
    )


def downgrade() -> None:
    """Best-effort schema rollback. Data inserted under the new schema is lost."""
    op.drop_table("session_dedupe")

    with op.batch_alter_table("device_tokens") as batch_op:
        batch_op.drop_index("ix_device_tokens_token_hash")
        batch_op.drop_index("ix_device_tokens_user_id")
    op.drop_table("device_tokens")

    op.drop_table("bundles")

    with op.batch_alter_table("triggers") as batch_op:
        batch_op.drop_index("ix_triggers_kpatch")
        batch_op.drop_index("ix_triggers_event")
    op.drop_table("triggers")

    op.drop_table("kpatches")

    # Recreate legacy rules + skills (empty) so session_dedupe FK can land.
    op.create_table(
        "rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_slug", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("on_event", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("match", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("inject", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("once_per_session", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["project_slug"], ["projects.slug"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("rules") as batch_op:
        batch_op.create_index("ix_rules_on_event", ["on_event"], unique=False)
        batch_op.create_index("ix_rules_project_slug", ["project_slug"], unique=False)
    op.create_table(
        "skills",
        sa.Column("project_slug", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("body", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("keywords", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["project_slug"], ["projects.slug"]),
        sa.PrimaryKeyConstraint("project_slug", "id"),
    )
    op.create_table(
        "session_dedupe",
        sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("fired_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["rules.id"]),
        sa.PrimaryKeyConstraint("session_id", "rule_id"),
    )

    # Revert projects: drop new columns + new FK + composite PK.
    bind = op.get_bind()
    with op.batch_alter_table("projects") as batch_op:
        if bind.dialect.name != "sqlite":
            batch_op.drop_constraint("fk_projects_org_id_orgs", type_="foreignkey")
        batch_op.drop_column("overridden_kpatches")
        batch_op.drop_column("disabled_kpatch_ids")
        batch_op.drop_column("attached_bundles")
        batch_op.drop_column("members")
        batch_op.drop_column("access_mode")
        batch_op.drop_column("org_id")
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("projects") as batch_op:
            batch_op.create_primary_key("pk_projects", ["slug"])
    else:
        op.drop_constraint("pk_projects", "projects", type_="primary")
        op.create_primary_key("projects_pkey", "projects", ["slug"])

    op.drop_table("org_members")
    op.drop_table("orgs")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_clerk_id")
    op.drop_table("users")
