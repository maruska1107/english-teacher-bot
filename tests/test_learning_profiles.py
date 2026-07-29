from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import User
from app.repositories.learning_profiles import LearningProfileRepository
from app.repositories.vocabulary_cards import VocabularyCardRepository


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _teacher(session: Session, telegram_user_id: int = 956230172) -> User:
    teacher = User(telegram_user_id=telegram_user_id, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    return teacher


def test_create_individual_profile_creates_student_and_membership():
    with _session() as session:
        teacher = _teacher(session)
        profiles = LearningProfileRepository(session)

        profile, student = profiles.create_individual_profile(teacher_user_id=teacher.id, student_name="Анна")
        session.commit()

        assert profile.name == "Анна"
        assert profile.profile_type == "individual"
        assert profile.card_publish_mode == "manual_review"
        assert student.name == "Анна"
        assert profile.memberships[0].student_id == student.id


def test_create_group_profile_creates_all_members():
    with _session() as session:
        teacher = _teacher(session)
        profiles = LearningProfileRepository(session)

        profile = profiles.create_group_profile(
            teacher_user_id=teacher.id,
            profile_name="Speaking B1",
            member_names=["Мария", "Катя", "Мария"],
        )
        session.commit()

        assert profile.name == "Speaking B1"
        assert profile.profile_type == "group"
        assert sorted(member.student.name for member in profile.memberships) == ["Катя", "Мария"]


def test_list_profiles_is_teacher_scoped():
    with _session() as session:
        teacher = _teacher(session, telegram_user_id=1)
        other_teacher = _teacher(session, telegram_user_id=2)
        profiles = LearningProfileRepository(session)
        profiles.create_individual_profile(teacher_user_id=teacher.id, student_name="Анна")
        profiles.create_individual_profile(teacher_user_id=other_teacher.id, student_name="Чужой ученик")
        session.commit()

        teacher_profiles = profiles.list_for_teacher(teacher.id)

        assert [profile.name for profile in teacher_profiles] == ["Анна"]


def test_vocabulary_card_repository_creates_draft_cards():
    with _session() as session:
        teacher = _teacher(session)
        profile, _student = LearningProfileRepository(session).create_individual_profile(
            teacher_user_id=teacher.id,
            student_name="Анна",
        )
        session.flush()
        cards_repo = VocabularyCardRepository(session)

        cards = cards_repo.create_draft_cards(
            teacher_user_id=teacher.id,
            learning_profile_id=profile.id,
            lesson_id=None,
            cards=[
                {
                    "term": "make progress",
                    "translation_ru": "делать успехи",
                    "definition_en": "to improve",
                    "example_sentence": "She made progress.",
                    "source_phrase": "make progress",
                    "level": "A2",
                },
                {
                    "term": "struggle with",
                    "translation_ru": "испытывать трудности с",
                    "definition_en": None,
                    "example_sentence": None,
                    "source_phrase": None,
                    "level": None,
                },
            ],
        )
        session.commit()

        assert [card.status for card in cards] == ["draft", "draft"]
        assert [card.term for card in profile.vocabulary_cards] == ["make progress", "struggle with"]
