from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.models import StudentHomework


class StudentHomeworkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def publish_current(
        self,
        *,
        student_id: int,
        learning_profile_id: int | None,
        lesson_id: int | None,
        lesson_date_label: str,
        summary_text: str,
        wins_text: str,
        focus_text: str,
        homework_items: list[str],
        new_cards_count: int,
    ) -> StudentHomework:
        previous = self._get_slot(student_id, "previous")
        if previous is not None:
            self.session.delete(previous)
            self.session.flush()

        current = self._get_slot(student_id, "current")
        if current is not None:
            current.slot = "previous"
            self.session.flush()

        homework = StudentHomework(
            student_id=student_id,
            learning_profile_id=learning_profile_id,
            lesson_id=lesson_id,
            slot="current",
            lesson_date_label=lesson_date_label.strip(),
            summary_text=summary_text.strip(),
            wins_text=wins_text.strip(),
            focus_text=focus_text.strip(),
            homework_items=[item.strip() for item in homework_items if item.strip()],
            new_cards_count=max(0, new_cards_count),
        )
        self.session.add(homework)
        self.session.flush()
        return homework

    def current_and_previous(self, student_id: int) -> list[StudentHomework]:
        slot_order = case((StudentHomework.slot == "current", 0), (StudentHomework.slot == "previous", 1), else_=2)
        return list(
            self.session.scalars(
                select(StudentHomework)
                .where(StudentHomework.student_id == student_id)
                .where(StudentHomework.slot.in_(["current", "previous"]))
                .order_by(slot_order, StudentHomework.updated_at.desc(), StudentHomework.id.desc())
            )
        )

    def _get_slot(self, student_id: int, slot: str) -> StudentHomework | None:
        return self.session.scalar(
            select(StudentHomework).where(StudentHomework.student_id == student_id, StudentHomework.slot == slot)
        )
