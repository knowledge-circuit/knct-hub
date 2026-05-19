"""trace_selection_columns

Add nullable columns to traces so each hook trace records which kpatches
contributed (kpatch_ids), which trigger rows matched (triggered_by),
and which project the hook was for (project_org_id, project_slug).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-19 00:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("traces") as batch_op:
        batch_op.add_column(
            sa.Column("kpatch_ids", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("triggered_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("project_org_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("project_slug", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.create_index("ix_traces_project_org_id", ["project_org_id"], unique=False)
        batch_op.create_index("ix_traces_project_slug", ["project_slug"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("traces") as batch_op:
        batch_op.drop_index("ix_traces_project_slug")
        batch_op.drop_index("ix_traces_project_org_id")
        batch_op.drop_column("project_slug")
        batch_op.drop_column("project_org_id")
        batch_op.drop_column("triggered_by")
        batch_op.drop_column("kpatch_ids")
