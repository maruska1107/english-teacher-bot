"""add zoom meeting subscriptions

Revision ID: 0004_zoom_meeting_subscriptions
Revises: 0003_transcript_url
Create Date: 2026-07-22 00:00:03.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_zoom_meeting_subscriptions"
down_revision: str | None = "0003_transcript_url"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "zoom_meeting_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("meeting_id", sa.String(length=64), nullable=False),
        sa.Column("meeting_url", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "meeting_id", name="uq_zoom_meeting_subscriptions_user_meeting"),
    )
    op.create_index(
        op.f("ix_zoom_meeting_subscriptions_meeting_id"),
        "zoom_meeting_subscriptions",
        ["meeting_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_zoom_meeting_subscriptions_user_id"),
        "zoom_meeting_subscriptions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_zoom_meeting_subscriptions_user_id"), table_name="zoom_meeting_subscriptions")
    op.drop_index(op.f("ix_zoom_meeting_subscriptions_meeting_id"), table_name="zoom_meeting_subscriptions")
    op.drop_table("zoom_meeting_subscriptions")
