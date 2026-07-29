from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StudentCardProgress(Base):
    __tablename__ = "student_card_progress"
    __table_args__ = (UniqueConstraint("student_id", "card_id", name="uq_student_card_progress_student_card"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("vocabulary_cards.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="new", nullable=False)
    review_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    student = relationship("Student", back_populates="card_progress")
    card = relationship("VocabularyCard", back_populates="student_progress")
