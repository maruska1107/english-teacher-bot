from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("meeting_uuid", name="uq_lessons_meeting_uuid"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    learning_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("learning_profiles.id", ondelete="SET NULL"), index=True
    )
    meeting_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    meeting_uuid: Mapped[str] = mapped_column(String(512), nullable=False)
    transcript_download_url: Mapped[str | None] = mapped_column(Text)
    transcript: Mapped[str | None] = mapped_column(Text)
    processing_status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    processing_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    teacher = relationship("User", back_populates="lessons")
    learning_profile = relationship("LearningProfile", back_populates="lessons")
    analysis = relationship("LessonAnalysis", back_populates="lesson", cascade="all, delete-orphan", uselist=False)
    vocabulary_cards = relationship("VocabularyCard", back_populates="lesson")
