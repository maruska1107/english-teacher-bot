from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models import User, ZoomToken
from app.zoom.settings_check import ZoomRecordingSettingsClient, ZoomSettingsCheckService


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory()


def add_teacher_with_zoom_token(session: Session) -> User:
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    session.add(
        ZoomToken(
            user_id=teacher.id,
            zoom_account_id="zoom-account-1",
            zoom_user_id="zoom-user-1",
            access_token="zoom-access-token",
            refresh_token="zoom-refresh-token",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    session.commit()
    return teacher


async def test_zoom_recording_settings_client_fetches_recording_settings_with_access_token():
    seen_requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(
            200,
            json={
                "recording": {
                    "cloud_recording": True,
                    "recording_audio_transcript": True,
                }
            },
        )

    client = ZoomRecordingSettingsClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    result = await client.get_recording_settings("zoom-access-token")

    assert result["recording"]["cloud_recording"] is True
    assert seen_requests[0].url == "https://api.zoom.us/v2/users/me/settings?option=recording"
    assert seen_requests[0].headers["Authorization"] == "Bearer zoom-access-token"


async def test_zoom_settings_check_service_reports_enabled_recording_settings():
    session = make_session()
    teacher = add_teacher_with_zoom_token(session)

    class FakeSettingsClient:
        async def get_recording_settings(self, access_token: str) -> dict:
            assert access_token == "zoom-access-token"
            return {
                "recording": {
                    "cloud_recording": True,
                    "recording_audio_transcript": True,
                }
            }

    result = await ZoomSettingsCheckService(session, FakeSettingsClient()).check_for_user(teacher.id)

    assert result.zoom_connected is True
    assert result.paid_plan_or_cloud_access is None
    assert result.cloud_recording_enabled is True
    assert result.audio_transcription_enabled is True


async def test_zoom_settings_check_service_reports_missing_settings_as_disabled():
    session = make_session()
    teacher = add_teacher_with_zoom_token(session)

    class FakeSettingsClient:
        async def get_recording_settings(self, access_token: str) -> dict:
            return {"recording": {"cloud_recording": False}}

    result = await ZoomSettingsCheckService(session, FakeSettingsClient()).check_for_user(teacher.id)

    assert result.zoom_connected is True
    assert result.cloud_recording_enabled is False
    assert result.audio_transcription_enabled is False


async def test_zoom_settings_check_service_reports_not_connected_without_token():
    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.commit()

    class FakeSettingsClient:
        async def get_recording_settings(self, access_token: str) -> dict:
            raise AssertionError("Zoom API should not be called without a token")

    result = await ZoomSettingsCheckService(session, FakeSettingsClient()).check_for_user(teacher.id)

    assert result.zoom_connected is False
    assert result.paid_plan_or_cloud_access is None
    assert result.cloud_recording_enabled is None
    assert result.audio_transcription_enabled is None
