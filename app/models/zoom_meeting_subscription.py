from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ZoomMeetingSubscription(Base):
    __tablename__ = "zoom_meeting_subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "meeting_id", name="uq_zoom_meeting_subscriptions_user_meeting"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    learning_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("learning_profiles.id", ondelete="SET NULL"), index=True
    )
    meeting_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    meeting_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="zoom_meeting_subscriptions")
    learning_profile = relationship("LearningProfile", back_populates="zoom_meeting_subscriptions")
