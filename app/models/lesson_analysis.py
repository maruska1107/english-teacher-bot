from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LessonAnalysis(Base):
    __tablename__ = "lesson_analysis"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), unique=True, index=True)
    analysis_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    teacher_report: Mapped[str] = mapped_column(Text, nullable=False)
    student_message: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lesson = relationship("Lesson", back_populates="analysis")
