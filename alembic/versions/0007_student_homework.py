"""add student homework snapshots

Revision ID: 0007_student_homework
Revises: 0006_vocabulary_card_images
Create Date: 2026-08-10 00:00:07.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_student_homework"
down_revision: str | None = "0006_vocabulary_card_images"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_homework",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("learning_profile_id", sa.Integer(), nullable=True),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("slot", sa.String(length=20), nullable=False),
        sa.Column("lesson_date_label", sa.String(length=255), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("wins_text", sa.Text(), nullable=False),
        sa.Column("focus_text", sa.Text(), nullable=False),
        sa.Column("homework_items", sa.JSON(), nullable=False),
        sa.Column("new_cards_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["learning_profile_id"], ["learning_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "slot", name="uq_student_homework_student_slot"),
    )
    op.create_index(op.f("ix_student_homework_student_id"), "student_homework", ["student_id"], unique=False)
    op.create_index(op.f("ix_student_homework_learning_profile_id"), "student_homework", ["learning_profile_id"], unique=False)
    op.create_index(op.f("ix_student_homework_lesson_id"), "student_homework", ["lesson_id"], unique=False)
    op.create_index(op.f("ix_student_homework_slot"), "student_homework", ["slot"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_student_homework_slot"), table_name="student_homework")
    op.drop_index(op.f("ix_student_homework_lesson_id"), table_name="student_homework")
    op.drop_index(op.f("ix_student_homework_learning_profile_id"), table_name="student_homework")
    op.drop_index(op.f("ix_student_homework_student_id"), table_name="student_homework")
    op.drop_table("student_homework")
