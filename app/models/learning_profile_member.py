from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LearningProfileMember(Base):
    __tablename__ = "learning_profile_members"
    __table_args__ = (UniqueConstraint("learning_profile_id", "student_id", name="uq_learning_profile_members_profile_student"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    learning_profile_id: Mapped[int] = mapped_column(
        ForeignKey("learning_profiles.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    learning_profile = relationship("LearningProfile", back_populates="memberships")
    student = relationship("Student", back_populates="memberships")
