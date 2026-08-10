from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import LearningProfile, Student, User
from app.repositories.student_homework import StudentHomeworkRepository


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory()


def seed_student(session: Session) -> tuple[Student, LearningProfile]:
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    student = Student(teacher_user_id=teacher.id, name="Аня", telegram_user_id=2002, invite_status="used")
    session.add(student)
    profile = LearningProfile(teacher_user_id=teacher.id, name="Аня", profile_type="individual")
    session.add(profile)
    session.commit()
    return student, profile


def test_publish_current_homework_creates_current_snapshot():
    session = make_session()
    student, profile = seed_student(session)
    repository = StudentHomeworkRepository(session)

    homework = repository.publish_current(
        student_id=student.id,
        learning_profile_id=profile.id,
        lesson_id=None,
        lesson_date_label="После урока 10 августа",
        summary_text="Сегодня говорили о путешествиях.",
        wins_text="Ты стала давать более длинные ответы.",
        focus_text="was / were",
        homework_items=["Exercise 4, page 32", "повторить 8 новых слов"],
        new_cards_count=8,
    )
    session.commit()

    assert homework.slot == "current"
    assert homework.student_id == student.id
    assert homework.learning_profile_id == profile.id
    assert homework.homework_items == ["Exercise 4, page 32", "повторить 8 новых слов"]
    assert repository.current_and_previous(student.id) == [homework]


def test_publish_current_homework_shifts_only_current_to_previous_and_discards_older_previous():
    session = make_session()
    student, profile = seed_student(session)
    repository = StudentHomeworkRepository(session)

    repository.publish_current(
        student_id=student.id,
        learning_profile_id=profile.id,
        lesson_id=None,
        lesson_date_label="После урока 1 августа",
        summary_text="Первый урок.",
        wins_text="Первый прогресс.",
        focus_text="Past Simple",
        homework_items=["old homework"],
        new_cards_count=3,
    )
    session.commit()
    repository.publish_current(
        student_id=student.id,
        learning_profile_id=profile.id,
        lesson_id=None,
        lesson_date_label="После урока 5 августа",
        summary_text="Второй урок.",
        wins_text="Второй прогресс.",
        focus_text="Questions",
        homework_items=["middle homework"],
        new_cards_count=5,
    )
    session.commit()
    repository.publish_current(
        student_id=student.id,
        learning_profile_id=profile.id,
        lesson_id=None,
        lesson_date_label="После урока 10 августа",
        summary_text="Третий урок.",
        wins_text="Третий прогресс.",
        focus_text="was / were",
        homework_items=["new homework"],
        new_cards_count=8,
    )
    session.commit()

    items = repository.current_and_previous(student.id)
    assert [(item.slot, item.summary_text, item.homework_items) for item in items] == [
        ("current", "Третий урок.", ["new homework"]),
        ("previous", "Второй урок.", ["middle homework"]),
    ]
    assert len(items) == 2
