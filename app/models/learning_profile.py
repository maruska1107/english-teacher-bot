from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LearningProfile(Base):
    __tablename__ = "learning_profiles"
    __table_args__ = (UniqueConstraint("teacher_user_id", "name", name="uq_learning_profiles_teacher_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_type: Mapped[str] = mapped_column(String(50), nullable=False)
    card_publish_mode: Mapped[str] = mapped_column(String(50), default="manual_review", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    teacher = relationship("User", back_populates="learning_profiles")
    memberships = relationship("LearningProfileMember", back_populates="learning_profile", cascade="all, delete-orphan")
    zoom_meeting_subscriptions = relationship("ZoomMeetingSubscription", back_populates="learning_profile")
    lessons = relationship("Lesson", back_populates="learning_profile")
    vocabulary_cards = relationship("VocabularyCard", back_populates="learning_profile", cascade="all, delete-orphan")
