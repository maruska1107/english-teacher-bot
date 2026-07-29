from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import StudentCardProgress


class StudentCardProgressRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create(self, student_id: int, card_id: int) -> StudentCardProgress:
        progress = self.session.scalar(
            select(StudentCardProgress).where(
                StudentCardProgress.student_id == student_id,
                StudentCardProgress.card_id == card_id,
            )
        )
        if progress is not None:
            return progress
        progress = StudentCardProgress(student_id=student_id, card_id=card_id, status="new", review_count=0)
        self.session.add(progress)
        self.session.flush()
        return progress

    def set_status(self, student_id: int, card_id: int, status: str) -> StudentCardProgress:
        progress = self.get_or_create(student_id=student_id, card_id=card_id)
        progress.status = status
        progress.review_count += 1
        progress.last_reviewed_at = datetime.now(UTC)
        self.session.flush()
        return progress
