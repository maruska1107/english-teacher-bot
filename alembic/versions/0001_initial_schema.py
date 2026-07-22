"""create initial mvp schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_user_id"),
    )
    op.create_index(op.f("ix_users_telegram_user_id"), "users", ["telegram_user_id"], unique=False)

    op.create_table(
        "processed_webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_processed_webhook_events_event_id"),
    )
    op.create_index(
        op.f("ix_processed_webhook_events_event_type"),
        "processed_webhook_events",
        ["event_type"],
        unique=False,
    )

    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_user_id", sa.Integer(), nullable=False),
        sa.Column("meeting_id", sa.String(length=255), nullable=False),
        sa.Column("meeting_uuid", sa.String(length=512), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("processing_status", sa.String(length=50), nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["teacher_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("meeting_uuid", name="uq_lessons_meeting_uuid"),
    )
    op.create_index(op.f("ix_lessons_meeting_id"), "lessons", ["meeting_id"], unique=False)
    op.create_index(op.f("ix_lessons_processing_status"), "lessons", ["processing_status"], unique=False)
    op.create_index(op.f("ix_lessons_teacher_user_id"), "lessons", ["teacher_user_id"], unique=False)

    op.create_table(
        "zoom_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("zoom_account_id", sa.String(length=255), nullable=False),
        sa.Column("zoom_user_id", sa.String(length=255), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "zoom_user_id", name="uq_zoom_tokens_user_zoom_user"),
    )
    op.create_index(op.f("ix_zoom_tokens_user_id"), "zoom_tokens", ["user_id"], unique=False)
    op.create_index(op.f("ix_zoom_tokens_zoom_account_id"), "zoom_tokens", ["zoom_account_id"], unique=False)
    op.create_index(op.f("ix_zoom_tokens_zoom_user_id"), "zoom_tokens", ["zoom_user_id"], unique=False)

    op.create_table(
        "lesson_analysis",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("analysis_json", sa.JSON(), nullable=False),
        sa.Column("teacher_report", sa.Text(), nullable=False),
        sa.Column("student_message", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lesson_analysis_lesson_id"), "lesson_analysis", ["lesson_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_lesson_analysis_lesson_id"), table_name="lesson_analysis")
    op.drop_table("lesson_analysis")
    op.drop_index(op.f("ix_zoom_tokens_zoom_user_id"), table_name="zoom_tokens")
    op.drop_index(op.f("ix_zoom_tokens_zoom_account_id"), table_name="zoom_tokens")
    op.drop_index(op.f("ix_zoom_tokens_user_id"), table_name="zoom_tokens")
    op.drop_table("zoom_tokens")
    op.drop_index(op.f("ix_lessons_teacher_user_id"), table_name="lessons")
    op.drop_index(op.f("ix_lessons_processing_status"), table_name="lessons")
    op.drop_index(op.f("ix_lessons_meeting_id"), table_name="lessons")
    op.drop_table("lessons")
    op.drop_index(op.f("ix_processed_webhook_events_event_type"), table_name="processed_webhook_events")
    op.drop_table("processed_webhook_events")
    op.drop_index(op.f("ix_users_telegram_user_id"), table_name="users")
    op.drop_table("users")
