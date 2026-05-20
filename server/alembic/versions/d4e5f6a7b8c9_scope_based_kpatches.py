"""scope_based_kpatches

Collapse to scope-based kpatches. Drop the bundle layer entirely:
- bundles table is removed
- orgs.default_bundles / orgs.include_unbundled removed
- projects.attached_bundles / disabled_kpatch_ids / overridden_kpatches removed

Kpatches gain explicit scope. Each row carries (scope, org_id,
project_slug, user_id, slug) where:
  scope ∈ {"org", "project", "member"}
  project_slug = "" when scope = "org"
  user_id = "" when scope != "member"

The table is recreated with a surrogate integer PK so triggers can FK by
single integer (instead of composite). Existing kpatch rows migrate as
scope="org". Existing trigger rows are re-keyed via lookup.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-19 02:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Drop bundles table outright.
    op.drop_table("bundles")

    # 2. Trim org and project bundle/override fields.
    with op.batch_alter_table("orgs") as batch_op:
        batch_op.drop_column("default_bundles")
        batch_op.drop_column("include_unbundled")
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("attached_bundles")
        batch_op.drop_column("disabled_kpatch_ids")
        batch_op.drop_column("overridden_kpatches")

    # 3. Build the new kpatches table side-by-side, copy existing as
    #    scope='org', re-key triggers, then swap.
    op.create_table(
        "kpatches_new",
        sa.Column("pk_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="org"),
        sa.Column("org_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("project_slug", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=""),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=""),
        sa.Column("slug", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("disable", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("body", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=""),
        sa.Column("keywords", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["orgs.id"]),
        sa.UniqueConstraint(
            "scope", "org_id", "project_slug", "user_id", "slug",
            name="uq_kpatch_scope_slug",
        ),
    )

    op.execute(
        sa.text(
            "INSERT INTO kpatches_new "
            "(scope, org_id, project_slug, user_id, slug, disable, "
            " name, description, body, keywords, created_at, updated_at) "
            "SELECT 'org', org_id, '', '', id, 0, "
            "       name, description, body, keywords, created_at, updated_at "
            "FROM kpatches"
        )
    )

    # Add temporary kpatch_pk_id on triggers and populate via join.
    with op.batch_alter_table("triggers") as batch_op:
        batch_op.add_column(sa.Column("kpatch_pk_id", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE triggers "
            "SET kpatch_pk_id = ("
            "  SELECT pk_id FROM kpatches_new "
            "  WHERE kpatches_new.scope = 'org' "
            "    AND kpatches_new.org_id = triggers.kpatch_org_id "
            "    AND kpatches_new.slug = triggers.kpatch_id"
            ")"
        )
    )

    # Restructure triggers around the new FK.
    inspector = sa.inspect(bind)
    trigger_indexes = {idx["name"] for idx in inspector.get_indexes("triggers")}
    with op.batch_alter_table("triggers") as batch_op:
        if "ix_triggers_kpatch" in trigger_indexes:
            batch_op.drop_index("ix_triggers_kpatch")
        batch_op.drop_column("kpatch_org_id")
        batch_op.drop_column("kpatch_id")
        batch_op.alter_column(
            "kpatch_pk_id", new_column_name="kpatch_id", nullable=False
        )

    op.drop_table("kpatches")
    op.rename_table("kpatches_new", "kpatches")

    # Recreate FK to point at the renamed kpatches.pk_id.
    with op.batch_alter_table("triggers") as batch_op:
        batch_op.create_foreign_key(
            "fk_triggers_kpatch",
            "kpatches",
            ["kpatch_id"],
            ["pk_id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_triggers_kpatch_id", ["kpatch_id"], unique=False)


def downgrade() -> None:
    """Best-effort. Loses any kpatches outside the org scope."""
    bind = op.get_bind()

    op.create_table(
        "kpatches_old",
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
    op.execute(
        sa.text(
            "INSERT INTO kpatches_old "
            "(org_id, id, name, description, body, keywords, created_at, updated_at) "
            "SELECT org_id, slug, name, description, body, keywords, created_at, updated_at "
            "FROM kpatches WHERE scope='org'"
        )
    )

    with op.batch_alter_table("triggers") as batch_op:
        batch_op.add_column(
            sa.Column("kpatch_org_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("kpatch_id_str", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
    op.execute(
        sa.text(
            "UPDATE triggers SET "
            "  kpatch_org_id = (SELECT org_id FROM kpatches WHERE kpatches.pk_id = triggers.kpatch_id), "
            "  kpatch_id_str  = (SELECT slug   FROM kpatches WHERE kpatches.pk_id = triggers.kpatch_id)"
        )
    )

    inspector = sa.inspect(bind)
    trigger_indexes = {idx["name"] for idx in inspector.get_indexes("triggers")}
    with op.batch_alter_table("triggers") as batch_op:
        if "ix_triggers_kpatch_id" in trigger_indexes:
            batch_op.drop_index("ix_triggers_kpatch_id")
        batch_op.drop_constraint("fk_triggers_kpatch", type_="foreignkey")
        batch_op.drop_column("kpatch_id")
        batch_op.alter_column("kpatch_id_str", new_column_name="kpatch_id", nullable=False)
        batch_op.alter_column("kpatch_org_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_triggers_kpatch_old",
            "kpatches_old",
            ["kpatch_org_id", "kpatch_id"],
            ["org_id", "id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_triggers_kpatch", ["kpatch_org_id", "kpatch_id"], unique=False)

    op.drop_table("kpatches")
    op.rename_table("kpatches_old", "kpatches")

    with op.batch_alter_table("orgs") as batch_op:
        batch_op.add_column(sa.Column("default_bundles", sqlmodel.sql.sqltypes.AutoString(),
                                       nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("include_unbundled", sa.Boolean(),
                                       nullable=False, server_default=sa.text("0")))
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("attached_bundles", sqlmodel.sql.sqltypes.AutoString(),
                                       nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("disabled_kpatch_ids", sqlmodel.sql.sqltypes.AutoString(),
                                       nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("overridden_kpatches", sqlmodel.sql.sqltypes.AutoString(),
                                       nullable=False, server_default="[]"))

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
