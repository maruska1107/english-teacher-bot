from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Student


class StudentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_teacher_and_name(self, teacher_user_id: int, name: str) -> Student | None:
        return self.session.scalar(
            select(Student).where(
                Student.teacher_user_id == teacher_user_id,
                Student.name == name,
            )
        )

    def get_or_create_for_teacher(self, teacher_user_id: int, name: str) -> Student:
        normalized_name = name.strip()
        existing = self.get_by_teacher_and_name(teacher_user_id, normalized_name)
        if existing is not None:
            return existing
        student = Student(teacher_user_id=teacher_user_id, name=normalized_name, invite_status="active")
        self.session.add(student)
        self.session.flush()
        return student
