"""add learning profiles and vocabulary cards

Revision ID: 0005_learning_profiles_cards
Revises: 0004_zoom_meeting_subscriptions
Create Date: 2026-07-29 00:00:05.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_learning_profiles_cards"
down_revision: str | None = "0004_zoom_meeting_subscriptions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=True),
        sa.Column("invite_token_hash", sa.String(length=128), nullable=True),
        sa.Column("invite_status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["teacher_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("teacher_user_id", "name", name="uq_students_teacher_name"),
    )
    op.create_index(op.f("ix_students_invite_token_hash"), "students", ["invite_token_hash"], unique=True)
    op.create_index(op.f("ix_students_teacher_user_id"), "students", ["teacher_user_id"], unique=False)
    op.create_index(op.f("ix_students_telegram_user_id"), "students", ["telegram_user_id"], unique=True)

    op.create_table(
        "learning_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("profile_type", sa.String(length=50), nullable=False),
        sa.Column("card_publish_mode", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["teacher_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("teacher_user_id", "name", name="uq_learning_profiles_teacher_name"),
    )
    op.create_index(
        op.f("ix_learning_profiles_teacher_user_id"),
        "learning_profiles",
        ["teacher_user_id"],
        unique=False,
    )

    op.create_table(
        "learning_profile_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("learning_profile_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["learning_profile_id"], ["learning_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "learning_profile_id",
            "student_id",
            name="uq_learning_profile_members_profile_student",
        ),
    )
    op.create_index(
        op.f("ix_learning_profile_members_learning_profile_id"),
        "learning_profile_members",
        ["learning_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learning_profile_members_student_id"),
        "learning_profile_members",
        ["student_id"],
        unique=False,
    )

    op.add_column("zoom_meeting_subscriptions", sa.Column("learning_profile_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_zoom_subs_learning_profile_id",
        "zoom_meeting_subscriptions",
        "learning_profiles",
        ["learning_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_zoom_meeting_subscriptions_learning_profile_id"),
        "zoom_meeting_subscriptions",
        ["learning_profile_id"],
        unique=False,
    )

    op.add_column("lessons", sa.Column("learning_profile_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_lessons_learning_profile_id_learning_profiles",
        "lessons",
        "learning_profiles",
        ["learning_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_lessons_learning_profile_id"), "lessons", ["learning_profile_id"], unique=False)

    op.create_table(
        "vocabulary_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_user_id", sa.Integer(), nullable=False),
        sa.Column("learning_profile_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("term", sa.String(length=255), nullable=False),
        sa.Column("translation_ru", sa.String(length=255), nullable=False),
        sa.Column("definition_en", sa.Text(), nullable=True),
        sa.Column("example_sentence", sa.Text(), nullable=True),
        sa.Column("source_phrase", sa.Text(), nullable=True),
        sa.Column("level", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["learning_profile_id"], ["learning_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["teacher_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vocabulary_cards_learning_profile_id"), "vocabulary_cards", ["learning_profile_id"])
    op.create_index(op.f("ix_vocabulary_cards_lesson_id"), "vocabulary_cards", ["lesson_id"])
    op.create_index(op.f("ix_vocabulary_cards_status"), "vocabulary_cards", ["status"])
    op.create_index(op.f("ix_vocabulary_cards_teacher_user_id"), "vocabulary_cards", ["teacher_user_id"])

    op.create_table(
        "student_card_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["vocabulary_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "card_id", name="uq_student_card_progress_student_card"),
    )
    op.create_index(op.f("ix_student_card_progress_card_id"), "student_card_progress", ["card_id"])
    op.create_index(op.f("ix_student_card_progress_student_id"), "student_card_progress", ["student_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_student_card_progress_student_id"), table_name="student_card_progress")
    op.drop_index(op.f("ix_student_card_progress_card_id"), table_name="student_card_progress")
    op.drop_table("student_card_progress")

    op.drop_index(op.f("ix_vocabulary_cards_teacher_user_id"), table_name="vocabulary_cards")
    op.drop_index(op.f("ix_vocabulary_cards_status"), table_name="vocabulary_cards")
    op.drop_index(op.f("ix_vocabulary_cards_lesson_id"), table_name="vocabulary_cards")
    op.drop_index(op.f("ix_vocabulary_cards_learning_profile_id"), table_name="vocabulary_cards")
    op.drop_table("vocabulary_cards")

    op.drop_index(op.f("ix_lessons_learning_profile_id"), table_name="lessons")
    op.drop_constraint("fk_lessons_learning_profile_id_learning_profiles", "lessons", type_="foreignkey")
    op.drop_column("lessons", "learning_profile_id")

    op.drop_index(op.f("ix_zoom_meeting_subscriptions_learning_profile_id"), table_name="zoom_meeting_subscriptions")
    op.drop_constraint(
        "fk_zoom_subs_learning_profile_id",
        "zoom_meeting_subscriptions",
        type_="foreignkey",
    )
    op.drop_column("zoom_meeting_subscriptions", "learning_profile_id")

    op.drop_index(op.f("ix_learning_profile_members_student_id"), table_name="learning_profile_members")
    op.drop_index(op.f("ix_learning_profile_members_learning_profile_id"), table_name="learning_profile_members")
    op.drop_table("learning_profile_members")

    op.drop_index(op.f("ix_learning_profiles_teacher_user_id"), table_name="learning_profiles")
    op.drop_table("learning_profiles")

    op.drop_index(op.f("ix_students_telegram_user_id"), table_name="students")
    op.drop_index(op.f("ix_students_teacher_user_id"), table_name="students")
    op.drop_index(op.f("ix_students_invite_token_hash"), table_name="students")
    op.drop_table("students")
