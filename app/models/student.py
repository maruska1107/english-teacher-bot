from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (UniqueConstraint("teacher_user_id", "name", name="uq_students_teacher_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    invite_token_hash: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    invite_status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    teacher = relationship("User", back_populates="students")
    memberships = relationship("LearningProfileMember", back_populates="student", cascade="all, delete-orphan")
    card_progress = relationship("StudentCardProgress", back_populates="student", cascade="all, delete-orphan")
