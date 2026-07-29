from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Lesson, LessonAnalysis, ZoomToken


class LessonRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def count_completed_for_teacher(self, teacher_user_id: int) -> int:
        return (
            self.session.scalar(
                select(func.count(Lesson.id)).where(
                    Lesson.teacher_user_id == teacher_user_id,
                    Lesson.processing_status == "completed",
                )
            )
            or 0
        )

    def count_all_completed(self) -> int:
        return self.session.scalar(select(func.count(Lesson.id)).where(Lesson.processing_status == "completed")) or 0

    def has_zoom_connection(self, teacher_user_id: int) -> bool:
        return (
            self.session.scalar(select(ZoomToken.id).where(ZoomToken.user_id == teacher_user_id).limit(1)) is not None
        )

    def latest_analysis_for_teacher(self, teacher_user_id: int) -> LessonAnalysis | None:
        return self.session.scalar(
            select(LessonAnalysis)
            .join(Lesson)
            .options(joinedload(LessonAnalysis.lesson))
            .where(Lesson.teacher_user_id == teacher_user_id)
            .order_by(desc(Lesson.created_at), desc(Lesson.id))
            .limit(1)
        )

    def latest_analysis(self) -> LessonAnalysis | None:
        return self.session.scalar(
            select(LessonAnalysis)
            .join(Lesson)
            .options(joinedload(LessonAnalysis.lesson))
            .order_by(desc(Lesson.created_at), desc(Lesson.id))
            .limit(1)
        )

    def latest_processing_error(self) -> str | None:
        return self.session.scalar(
            select(Lesson.processing_error)
            .where(Lesson.processing_error.is_not(None))
            .order_by(desc(Lesson.updated_at), desc(Lesson.id))
            .limit(1)
        )
