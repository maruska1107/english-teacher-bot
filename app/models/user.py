from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="teacher", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    zoom_tokens = relationship("ZoomToken", back_populates="user", cascade="all, delete-orphan")
    zoom_meeting_subscriptions = relationship(
        "ZoomMeetingSubscription", back_populates="user", cascade="all, delete-orphan"
    )
    lessons = relationship("Lesson", back_populates="teacher", cascade="all, delete-orphan")
