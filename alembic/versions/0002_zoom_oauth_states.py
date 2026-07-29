"""add zoom oauth states

Revision ID: 0002_zoom_oauth_states
Revises: 0001_initial_schema
Create Date: 2026-07-22 00:00:01.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_zoom_oauth_states"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "zoom_oauth_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_zoom_oauth_states_state"), "zoom_oauth_states", ["state"], unique=True)
    op.create_index(op.f("ix_zoom_oauth_states_user_id"), "zoom_oauth_states", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_zoom_oauth_states_user_id"), table_name="zoom_oauth_states")
    op.drop_index(op.f("ix_zoom_oauth_states_state"), table_name="zoom_oauth_states")
    op.drop_table("zoom_oauth_states")
