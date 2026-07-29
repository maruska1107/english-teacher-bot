from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VocabularyCard(Base):
    __tablename__ = "vocabulary_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    learning_profile_id: Mapped[int] = mapped_column(ForeignKey("learning_profiles.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"), index=True)
    term: Mapped[str] = mapped_column(String(255), nullable=False)
    translation_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    definition_en: Mapped[str | None] = mapped_column(Text)
    example_sentence: Mapped[str | None] = mapped_column(Text)
    source_phrase: Mapped[str | None] = mapped_column(Text)
    level: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    teacher = relationship("User", back_populates="vocabulary_cards")
    learning_profile = relationship("LearningProfile", back_populates="vocabulary_cards")
    lesson = relationship("Lesson", back_populates="vocabulary_cards")
    student_progress = relationship("StudentCardProgress", back_populates="card", cascade="all, delete-orphan")
