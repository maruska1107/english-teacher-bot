from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from app.models import Lesson, LessonAnalysis, ProcessedWebhookEvent, User, ZoomToken


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
