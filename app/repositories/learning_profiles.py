from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import LearningProfile, LearningProfileMember, Student
from app.repositories.students import StudentRepository


class LearningProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.students = StudentRepository(session)

    def create_individual_profile(self, teacher_user_id: int, student_name: str) -> tuple[LearningProfile, Student]:
        student = self.students.get_or_create_for_teacher(teacher_user_id=teacher_user_id, name=student_name)
        profile = LearningProfile(
            teacher_user_id=teacher_user_id,
            name=student.name,
            profile_type="individual",
            card_publish_mode="manual_review",
        )
        self.session.add(profile)
        self.session.flush()
        self.session.add(LearningProfileMember(learning_profile_id=profile.id, student_id=student.id))
        self.session.flush()
        self.session.refresh(profile)
        return profile, student

    def create_group_profile(self, teacher_user_id: int, profile_name: str, member_names: list[str]) -> LearningProfile:
        profile = LearningProfile(
            teacher_user_id=teacher_user_id,
            name=profile_name.strip(),
            profile_type="group",
            card_publish_mode="manual_review",
        )
        self.session.add(profile)
        self.session.flush()

        seen_names: set[str] = set()
        for raw_name in member_names:
            name = raw_name.strip()
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            student = self.students.get_or_create_for_teacher(teacher_user_id=teacher_user_id, name=name)
            self.session.add(LearningProfileMember(learning_profile_id=profile.id, student_id=student.id))
        self.session.flush()
        self.session.refresh(profile)
        return profile

    def list_for_teacher(self, teacher_user_id: int) -> list[LearningProfile]:
        return list(
            self.session.scalars(
                select(LearningProfile)
                .options(selectinload(LearningProfile.memberships).selectinload(LearningProfileMember.student))
                .where(LearningProfile.teacher_user_id == teacher_user_id)
                .order_by(LearningProfile.created_at, LearningProfile.id)
            )
        )
