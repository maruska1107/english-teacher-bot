from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StudentHomework(Base):
    __tablename__ = "student_homework"
    __table_args__ = (UniqueConstraint("student_id", "slot", name="uq_student_homework_student_slot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    learning_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("learning_profiles.id", ondelete="SET NULL"), index=True
    )
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"), index=True)
    slot: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    lesson_date_label: Mapped[str] = mapped_column(String(255), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    wins_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    focus_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    homework_items: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    new_cards_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    student = relationship("Student")
    learning_profile = relationship("LearningProfile")
    lesson = relationship("Lesson")
