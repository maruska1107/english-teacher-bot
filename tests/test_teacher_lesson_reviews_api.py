import hashlib
import hmac
import json
from urllib.parse import quote

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_app
from app.models import (
    LearningProfile,
    LearningProfileMember,
    Lesson,
    LessonAnalysis,
    Student,
    StudentHomework,
    User,
    VocabularyCard,
)


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory()


def make_settings() -> Settings:
    return Settings(app_env="test", telegram_bot_token="test-bot-token", allowed_telegram_teacher_ids="1001,2002")


def signed_init_data(telegram_user_id: int, bot_token: str = "test-bot-token") -> str:
    fields = {
        "auth_date": "1780000000",
        "query_id": "teacher-reviews-test",
        "user": json.dumps({"id": telegram_user_id, "first_name": "Teacher"}, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return "&".join(f"{key}={quote(value)}" for key, value in {**fields, "hash": signature}.items())


def make_client(session: Session) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = make_settings

    def override_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    return TestClient(app)


def seed_review_lesson(session: Session) -> tuple[User, Student, LearningProfile, Lesson]:
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    other_teacher = User(telegram_user_id=2002, role="teacher", is_active=True)
    session.add_all([teacher, other_teacher])
    session.flush()
    student = Student(teacher_user_id=teacher.id, name="Аня", telegram_user_id=3003, invite_status="used")
    profile = LearningProfile(teacher_user_id=teacher.id, name="Аня", profile_type="individual")
    session.add_all([student, profile])
    session.flush()
    session.add(LearningProfileMember(learning_profile_id=profile.id, student_id=student.id))
    lesson = Lesson(
        teacher_user_id=teacher.id,
        learning_profile_id=profile.id,
        meeting_id="lesson-1",
        meeting_uuid="lesson-review-1",
        processing_status="completed",
    )
    session.add(lesson)
    session.flush()
    session.add(
        LessonAnalysis(
            lesson_id=lesson.id,
            analysis_json={
                "summary": "Сегодня говорили о путешествиях и Past Simple.",
                "strengths": ["Ты стала давать более длинные ответы."],
                "mistakes": [
                    {
                        "quote": "We was in Italy.",
                        "correction": "We were in Italy.",
                        "explanation": "После we используем were.",
                    }
                ],
                "homework": ["Exercise 4, page 32", "повторить 8 новых слов"],
                "vocabulary_cards": [],
            },
            teacher_report="Отчёт по уроку\n\nДомашнее задание:\n- Exercise 4, page 32",
            student_message="✨ Аня, итоги сегодняшнего урока готовы",
            model="test",
            prompt_version="test-v1",
        )
    )
    session.add(
        VocabularyCard(
            teacher_user_id=teacher.id,
            learning_profile_id=profile.id,
            lesson_id=lesson.id,
            term="journey",
            translation_ru="путешествие",
            status="draft",
        )
    )
    session.add(
        VocabularyCard(
            teacher_user_id=teacher.id,
            learning_profile_id=profile.id,
            lesson_id=lesson.id,
            term="fluency",
            translation_ru="беглость речи",
            status="draft",
        )
    )
    session.commit()
    return teacher, student, profile, lesson


def test_teacher_can_list_pending_lesson_reviews():
    session = make_session()
    _, _, _, lesson = seed_review_lesson(session)
    client = make_client(session)

    response = client.get("/api/teacher/lesson-reviews", headers={"x-telegram-init-data": signed_init_data(1001)})

    assert response.status_code == 200
    assert response.json() == {
        "reviews": [
            {
                "lesson_id": lesson.id,
                "student_name": "Аня",
                "lesson_date_label": "После урока",
                "summary_text": "Сегодня говорили о путешествиях и Past Simple.",
                "homework_items": ["Exercise 4, page 32", "повторить 8 новых слов"],
                "new_cards_count": 2,
                "profile_id": lesson.learning_profile_id,
                "cards": [
                    {
                        "id": lesson.vocabulary_cards[1].id,
                        "learning_profile_id": lesson.learning_profile_id,
                        "term": "fluency",
                        "translation_ru": "беглость речи",
                        "definition_en": None,
                        "example_sentence": None,
                        "source_phrase": None,
                        "level": None,
                        "status": "draft",
                        "image_url": None,
                        "image_source_url": None,
                        "image_creator": None,
                        "image_license": None,
                        "image_license_url": None,
                        "image_search_query": None,
                    },
                    {
                        "id": lesson.vocabulary_cards[0].id,
                        "learning_profile_id": lesson.learning_profile_id,
                        "term": "journey",
                        "translation_ru": "путешествие",
                        "definition_en": None,
                        "example_sentence": None,
                        "source_phrase": None,
                        "level": None,
                        "status": "draft",
                        "image_url": None,
                        "image_source_url": None,
                        "image_creator": None,
                        "image_license": None,
                        "image_license_url": None,
                        "image_search_query": None,
                    },
                ],
            }
        ]
    }


def test_teacher_confirm_publishes_homework_and_removes_pending_review():
    session = make_session()
    _, student, _, lesson = seed_review_lesson(session)
    client = make_client(session)

    response = client.post(
        f"/api/teacher/lesson-reviews/{lesson.id}/confirm",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )

    assert response.status_code == 200
    assert response.json()["slot"] == "current"
    homework = (
        session.query(StudentHomework)
        .filter_by(student_id=student.id, lesson_id=lesson.id, slot="current")
        .one()
    )
    assert homework.summary_text == "Сегодня говорили о путешествиях и Past Simple."
    assert homework.wins_text == "Ты стала давать более длинные ответы."
    assert "We was in Italy." in homework.focus_text
    assert homework.homework_items == ["Exercise 4, page 32", "повторить 8 новых слов"]
    assert homework.new_cards_count == 2
    assert {card.status for card in lesson.vocabulary_cards} == {"published"}

    pending = client.get("/api/teacher/lesson-reviews", headers={"x-telegram-init-data": signed_init_data(1001)})
    assert pending.json() == {"reviews": []}


def test_teacher_can_edit_and_delete_review_draft_cards_before_confirm():
    session = make_session()
    _, _, _, lesson = seed_review_lesson(session)
    client = make_client(session)
    journey_card, fluency_card = sorted(lesson.vocabulary_cards, key=lambda card: card.term)

    updated = client.patch(
        f"/api/teacher/lesson-reviews/cards/{journey_card.id}",
        headers={"x-telegram-init-data": signed_init_data(1001)},
        json={"term": "journey updated", "translation_ru": "поездка", "example_sentence": "A long journey."},
    )
    deleted = client.delete(
        f"/api/teacher/lesson-reviews/cards/{fluency_card.id}",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )
    confirmed = client.post(
        f"/api/teacher/lesson-reviews/{lesson.id}/confirm",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )

    assert updated.status_code == 200
    assert updated.json()["term"] == "journey updated"
    assert deleted.status_code == 204
    assert confirmed.status_code == 200
    cards = session.query(VocabularyCard).filter_by(lesson_id=lesson.id).all()
    assert [(card.term, card.status) for card in cards] == [("journey updated", "published")]


def test_teacher_review_confirm_publishes_only_cards_from_that_lesson():
    session = make_session()
    _, _, profile, lesson = seed_review_lesson(session)
    client = make_client(session)
    manual_card = VocabularyCard(
        teacher_user_id=lesson.teacher_user_id,
        learning_profile_id=profile.id,
        lesson_id=None,
        term="manual",
        translation_ru="ручная",
        status="draft",
    )
    session.add(manual_card)
    session.commit()

    response = client.post(
        f"/api/teacher/lesson-reviews/{lesson.id}/confirm",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )

    assert response.status_code == 200
    assert {card.status for card in lesson.vocabulary_cards} == {"published"}
    assert manual_card.status == "draft"


def test_teacher_cannot_edit_foreign_or_published_review_card():
    session = make_session()
    _, _, _, lesson = seed_review_lesson(session)
    client = make_client(session)
    card = lesson.vocabulary_cards[0]

    foreign = client.patch(
        f"/api/teacher/lesson-reviews/cards/{card.id}",
        headers={"x-telegram-init-data": signed_init_data(2002)},
        json={"term": "bad"},
    )
    card.status = "published"
    session.commit()
    published = client.delete(
        f"/api/teacher/lesson-reviews/cards/{card.id}",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )

    assert foreign.status_code == 404
    assert published.status_code == 404


def test_teacher_confirm_rejects_repeated_or_foreign_lesson():
    session = make_session()
    _, _, _, lesson = seed_review_lesson(session)
    client = make_client(session)

    foreign = client.post(
        f"/api/teacher/lesson-reviews/{lesson.id}/confirm",
        headers={"x-telegram-init-data": signed_init_data(2002)},
    )
    first = client.post(
        f"/api/teacher/lesson-reviews/{lesson.id}/confirm",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )
    repeated = client.post(
        f"/api/teacher/lesson-reviews/{lesson.id}/confirm",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )

    assert foreign.status_code == 404
    assert first.status_code == 200
    assert repeated.status_code == 409


def test_teacher_can_view_current_and_previous_homework_for_own_profile():
    session = make_session()
    _, student, profile, lesson = seed_review_lesson(session)
    client = make_client(session)
    session.add(
        StudentHomework(
            student_id=student.id,
            learning_profile_id=profile.id,
            lesson_id=lesson.id,
            slot="current",
            lesson_date_label="После урока",
            summary_text="Текущее ДЗ",
            wins_text="Сильная речь",
            focus_text="Past Simple",
            homework_items=["Exercise 4"],
            new_cards_count=2,
        )
    )
    session.add(
        StudentHomework(
            student_id=student.id,
            learning_profile_id=profile.id,
            lesson_id=None,
            slot="previous",
            lesson_date_label="Предыдущий урок",
            summary_text="Предыдущее ДЗ",
            wins_text="",
            focus_text="",
            homework_items=["Read page 12"],
            new_cards_count=1,
        )
    )
    session.commit()

    response = client.get(
        f"/api/teacher/homework?profile_id={profile.id}",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )
    foreign = client.get(
        f"/api/teacher/homework?profile_id={profile.id}",
        headers={"x-telegram-init-data": signed_init_data(2002)},
    )

    assert response.status_code == 200
    assert [item["slot"] for item in response.json()["items"]] == ["current", "previous"]
    assert response.json()["items"][0]["summary_text"] == "Текущее ДЗ"
    assert response.json()["items"][1]["homework_items"] == ["Read page 12"]
    assert foreign.status_code == 404
