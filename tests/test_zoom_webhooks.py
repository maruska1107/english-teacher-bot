import hashlib
import hmac
import json
import time
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.zoom import get_lesson_processing_service
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_app
from app.models import LearningProfile, Lesson, ProcessedWebhookEvent, User, ZoomMeetingSubscription, ZoomToken


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
    return Settings(
        app_env="test",
        allowed_telegram_teacher_ids="1001",
        zoom_client_id="zoom-client-id",
        zoom_client_secret="zoom-client-secret",
        zoom_redirect_uri="https://bot.example.com/api/zoom/oauth/callback",
        zoom_webhook_secret_token="webhook-secret",
        auto_process_zoom_webhook_lessons=False,
    )


def signed_headers(payload: dict, secret: str = "webhook-secret", timestamp: str | None = None) -> dict[str, str]:
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = timestamp or str(int(time.time()))
    message = b"v0:" + timestamp.encode() + b":" + body
    signature = "v0=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return {
        "x-zm-request-timestamp": timestamp,
        "x-zm-signature": signature,
        "content-type": "application/json",
    }


def make_client(session: Session) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = make_settings

    def override_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    return TestClient(app)


def test_zoom_url_validation_returns_encrypted_token():
    session = make_session()
    client = make_client(session)
    payload = {"event": "endpoint.url_validation", "payload": {"plainToken": "plain-token"}}

    response = client.post(
        "/api/zoom/webhook",
        content=json.dumps(payload, separators=(",", ":")),
        headers=signed_headers(payload),
    )

    assert response.status_code == 200
    assert response.json() == {
        "plainToken": "plain-token",
        "encryptedToken": hmac.new(b"webhook-secret", b"plain-token", hashlib.sha256).hexdigest(),
    }


def test_zoom_webhook_rejects_invalid_signature():
    session = make_session()
    client = make_client(session)
    payload = {"event": "recording.completed", "event_ts": 1, "payload": {}}
    headers = signed_headers(payload, secret="wrong-secret")

    response = client.post("/api/zoom/webhook", content=json.dumps(payload, separators=(",", ":")), headers=headers)

    assert response.status_code == 401


def test_recording_completed_is_idempotent_and_creates_lesson_for_zoom_user():
    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    session.add(
        ZoomToken(
            user_id=teacher.id,
            zoom_account_id="account-1",
            zoom_user_id="zoom-user-1",
            access_token="access",
            refresh_token="refresh",
            expires_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    profile = LearningProfile(
        teacher_user_id=teacher.id,
        name="Speaking B1",
        profile_type="group",
        card_publish_mode="manual_review",
    )
    session.add(profile)
    session.flush()
    session.add(
        ZoomMeetingSubscription(
            user_id=teacher.id,
            learning_profile_id=profile.id,
            meeting_id="987654321",
            meeting_url="https://us06web.zoom.us/j/987654321",
            is_active=True,
        )
    )
    session.commit()
    client = make_client(session)
    payload = {
        "event": "recording.completed",
        "event_ts": 123,
        "payload": {
            "account_id": "account-1",
            "object": {
                "id": "987654321",
                "uuid": "meeting-uuid-1",
                "host_id": "zoom-user-1",
                "recording_files": [
                    {
                        "id": "file-1",
                        "file_type": "TRANSCRIPT",
                        "download_url": "https://zoom.example/transcript.vtt",
                    }
                ],
            },
        },
    }
    body = json.dumps(payload, separators=(",", ":"))
    headers = signed_headers(payload)

    first_response = client.post("/api/zoom/webhook", content=body, headers=headers)
    second_response = client.post("/api/zoom/webhook", content=body, headers=headers)

    assert first_response.status_code == 200
    assert first_response.json() == {"status": "accepted"}
    assert second_response.status_code == 200
    assert second_response.json() == {"status": "already_processed"}
    lesson = session.query(Lesson).one()
    assert lesson.teacher_user_id == teacher.id
    assert lesson.learning_profile_id == profile.id
    assert lesson.meeting_id == "987654321"
    assert lesson.meeting_uuid == "meeting-uuid-1"
    assert lesson.transcript_download_url == "https://zoom.example/transcript.vtt"
    assert lesson.processing_status == "pending"
    processed_event_count = (
        session.query(ProcessedWebhookEvent).filter_by(event_id="recording.completed:meeting-uuid-1:123").count()
    )
    assert processed_event_count == 1


class FakeLessonProcessor:
    def __init__(self) -> None:
        self.lesson_ids: list[int] = []

    async def process_lesson(self, lesson_id: int) -> None:
        self.lesson_ids.append(lesson_id)


def test_recording_completed_can_trigger_lesson_processing_pipeline():
    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    session.add(
        ZoomToken(
            user_id=teacher.id,
            zoom_account_id="account-1",
            zoom_user_id="zoom-user-1",
            access_token="access",
            refresh_token="refresh",
            expires_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    session.add(
        ZoomMeetingSubscription(
            user_id=teacher.id,
            meeting_id="987654322",
            meeting_url="https://us06web.zoom.us/j/987654322",
            is_active=True,
        )
    )
    session.commit()
    client = make_client(session)
    app = client.app
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="test",
        allowed_telegram_teacher_ids="1001",
        zoom_webhook_secret_token="webhook-secret",
        auto_process_zoom_webhook_lessons=True,
    )
    fake_processor = FakeLessonProcessor()
    app.dependency_overrides[get_lesson_processing_service] = lambda: fake_processor
    payload = {
        "event": "recording.completed",
        "event_ts": 124,
        "payload": {
            "account_id": "account-1",
            "object": {
                "id": "987654322",
                "uuid": "meeting-uuid-2",
                "host_id": "zoom-user-1",
                "recording_files": [
                    {
                        "id": "file-2",
                        "file_type": "TRANSCRIPT",
                        "download_url": "https://zoom.example/transcript.vtt",
                    }
                ],
            },
        },
    }

    response = client.post(
        "/api/zoom/webhook",
        content=json.dumps(payload, separators=(",", ":")),
        headers=signed_headers(payload),
    )

    assert response.status_code == 200
    assert fake_processor.lesson_ids == [session.query(Lesson).one().id]


def test_recording_completed_ignores_unsubscribed_meeting():
    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    session.add(
        ZoomToken(
            user_id=teacher.id,
            zoom_account_id="account-1",
            zoom_user_id="zoom-user-1",
            access_token="access",
            refresh_token="refresh",
            expires_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    session.add(
        ZoomMeetingSubscription(
            user_id=teacher.id,
            meeting_id="111222333",
            meeting_url="https://us06web.zoom.us/j/111222333",
            is_active=True,
        )
    )
    session.commit()
    client = make_client(session)
    payload = {
        "event": "recording.completed",
        "event_ts": 125,
        "payload": {
            "account_id": "account-1",
            "object": {
                "id": "987654323",
                "uuid": "meeting-uuid-3",
                "host_id": "zoom-user-1",
                "recording_files": [
                    {
                        "id": "file-3",
                        "file_type": "TRANSCRIPT",
                        "download_url": "https://zoom.example/transcript.vtt",
                    }
                ],
            },
        },
    }

    response = client.post(
        "/api/zoom/webhook",
        content=json.dumps(payload, separators=(",", ":")),
        headers=signed_headers(payload),
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored_unsubscribed_meeting"}
    assert session.query(Lesson).count() == 0
