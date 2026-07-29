from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from app.models import (
    LearningProfile,
    LearningProfileMember,
    Lesson,
    LessonAnalysis,
    ProcessedWebhookEvent,
    Student,
    StudentCardProgress,
    User,
    VocabularyCard,
    ZoomMeetingSubscription,
    ZoomToken,
)


def test_settings_build_database_url_from_parts_when_not_explicit():
    settings = Settings(
        app_env="test",
        postgres_user="teacher",
        postgres_password="secret",
        postgres_host="db",
        postgres_port=5432,
        postgres_db="english_teacher_bot",
        telegram_bot_token="token",
        allowed_telegram_teacher_ids="1001, 1002",
        telegram_admin_id=999,
        zoom_client_id="zoom-client",
        zoom_client_secret="zoom-secret",
        zoom_redirect_uri="https://example.com/api/zoom/oauth/callback",
        zoom_webhook_secret_token="webhook-secret",
        openai_api_key="openai-key",
    )

    assert str(settings.database_url) == ("postgresql+psycopg://teacher:secret@db:5432/english_teacher_bot")
    assert settings.allowed_teacher_ids == [1001, 1002]


def test_health_endpoint_returns_static_status_without_database():
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "english-teacher-bot"}


def test_zoom_landing_page_explains_oauth_flow():
    app = create_app()
    client = TestClient(app)

    root_response = client.get("/")
    assert root_response.status_code == 200
    assert "ZOOM_verify_c5df37580d2446f59658896a833eec7a" in root_response.text

    root_head_response = client.head("/")
    assert root_head_response.status_code == 200

    response = client.get("/zoom")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "English Tutor AI" in response.text
    assert "Open Telegram Bot" in response.text
    assert "https://t.me/EnglishTutorHelperAIBot" in response.text
    assert "ZOOM_verify_c5df37580d2446f59658896a833eec7a" in response.text
    assert "does not store video recordings" in response.text
    assert "/connect_zoom" in response.text

    head_response = client.head("/zoom")

    assert head_response.status_code == 200
    assert head_response.headers["content-type"].startswith("text/html")


def test_teacher_cards_webapp_page_is_available():
    app = create_app()
    client = TestClient(app)

    response = client.get("/teacher/cards")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Telegram.WebApp" in response.text
    assert "x-telegram-init-data" in response.text
    assert "/api/teacher/cards?status=draft" in response.text
    assert "publish" in response.text
    assert "archive" in response.text

    head_response = client.head("/teacher/cards")
    assert head_response.status_code == 200


def test_student_cards_webapp_page_is_available():
    app = create_app()
    client = TestClient(app)

    response = client.get("/student/cards")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Telegram.WebApp" in response.text
    assert "x-telegram-init-data" in response.text
    assert "/api/student/cards" in response.text
    assert "Режим заучивания" in response.text
    assert "Нажмите, чтобы перевернуть" in response.text
    assert "studyCards" in response.text
    assert 'card.status !== "known"' in response.text
    assert "flipCard" in response.text
    assert "Не знаю" in response.text
    assert "Ещё учу" in response.text
    assert "Знаю" in response.text
    assert "Учить" in response.text
    assert "data-list-progress" in response.text
    assert "min-height: 340px" in response.text
    assert "overflow-y: auto" in response.text

    head_response = client.head("/student/cards")
    assert head_response.status_code == 200


def test_marketplace_required_pages_are_available():
    app = create_app()
    client = TestClient(app)

    expected_pages = {
        "/privacy": ["Privacy Policy", "data subject rights", "Zoom OAuth", "video recordings"],
        "/terms": ["Terms of Use", "English Tutor AI", "Zoom", "Telegram"],
        "/support": ["Support", "EnglishTutorHelperAIBot", "Telegram"],
        "/documentation": ["Zoom App Documentation", "/connect_zoom", "/disconnect_zoom", "remove"],
    }

    for path, expected_texts in expected_pages.items():
        response = client.get(path)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        for expected_text in expected_texts:
            assert expected_text in response.text

        head_response = client.head(path)
        assert head_response.status_code == 200


def test_database_schema_supports_learning_profiles_and_cards():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        teacher = User(telegram_user_id=956230172, role="teacher", is_active=True)
        session.add(teacher)
        session.flush()

        student = Student(
            teacher_user_id=teacher.id,
            name="Анна",
            telegram_user_id=111222333,
            invite_token_hash="hashed-token",
            invite_status="active",
        )
        profile = LearningProfile(
            teacher_user_id=teacher.id,
            name="Анна",
            profile_type="individual",
            card_publish_mode="manual_review",
        )
        session.add_all([student, profile])
        session.flush()

        membership = LearningProfileMember(
            learning_profile_id=profile.id,
            student_id=student.id,
        )
        subscription = ZoomMeetingSubscription(
            user_id=teacher.id,
            learning_profile_id=profile.id,
            meeting_id="987654321",
            meeting_url="https://example.zoom.us/j/987654321",
            is_active=True,
        )
        lesson = Lesson(
            teacher_user_id=teacher.id,
            learning_profile_id=profile.id,
            meeting_id="987654321",
            meeting_uuid="meeting-uuid-learning-profile",
            processing_status="completed",
        )
        session.add_all([membership, subscription, lesson])
        session.flush()

        card = VocabularyCard(
            teacher_user_id=teacher.id,
            learning_profile_id=profile.id,
            lesson_id=lesson.id,
            term="make progress",
            translation_ru="делать успехи",
            definition_en="to improve",
            example_sentence="She made progress with pronunciation.",
            source_phrase="make progress",
            level="A2",
            status="draft",
        )
        session.add(card)
        session.flush()

        progress = StudentCardProgress(
            student_id=student.id,
            card_id=card.id,
            status="new",
            review_count=0,
        )
        session.add(progress)
        session.commit()

        saved_profile = session.get(LearningProfile, profile.id)
        assert saved_profile.teacher.telegram_user_id == 956230172
        assert saved_profile.memberships[0].student.name == "Анна"
        assert saved_profile.zoom_meeting_subscriptions[0].meeting_id == "987654321"
        assert saved_profile.lessons[0].meeting_uuid == "meeting-uuid-learning-profile"
        assert saved_profile.vocabulary_cards[0].term == "make progress"
        assert saved_profile.vocabulary_cards[0].student_progress[0].student.name == "Анна"


def test_database_schema_supports_required_user_owned_entities():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(telegram_user_id=123456789, role="teacher", is_active=True)
        session.add(user)
        session.flush()

        token = ZoomToken(
            user_id=user.id,
            zoom_account_id="account-1",
            zoom_user_id="zoom-user-1",
            access_token="encrypted-access-token",
            refresh_token="encrypted-refresh-token",
            expires_at=datetime.now(UTC),
        )
        lesson = Lesson(
            teacher_user_id=user.id,
            meeting_id="987654321",
            meeting_uuid="meeting-uuid",
            transcript="WEBVTT\n\n00:00:00.000 --> 00:00:03.000\nHello!",
            processing_status="pending",
        )
        session.add_all([token, lesson])
        session.flush()

        analysis = LessonAnalysis(
            lesson_id=lesson.id,
            analysis_json={"summary": "Short summary"},
            teacher_report="Teacher report",
            student_message="Student message",
            model="gpt-4.1-mini",
            prompt_version="v1",
        )
        event = ProcessedWebhookEvent(
            event_id="event-1",
            event_type="recording.transcript_completed",
            status="processed",
        )
        session.add_all([analysis, event])
        session.commit()

        saved_lesson = session.get(Lesson, lesson.id)
        assert saved_lesson.teacher.telegram_user_id == 123456789
        assert saved_lesson.analysis.teacher_report == "Teacher report"
        assert session.query(ZoomToken).filter_by(user_id=user.id).one().zoom_user_id == "zoom-user-1"
        assert session.query(ProcessedWebhookEvent).filter_by(event_id="event-1").one().status == "processed"
