from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from sqlalchemy.orm import Session

from app.repositories.zoom_tokens import ZoomTokenRepository

ZOOM_USER_SETTINGS_URL = "https://api.zoom.us/v2/users/me/settings"


@dataclass(frozen=True)
class ZoomSettingsCheckResult:
    zoom_connected: bool
    paid_plan_or_cloud_access: bool | None
    cloud_recording_enabled: bool | None
    audio_transcription_enabled: bool | None


class ZoomRecordingSettingsClientProtocol(Protocol):
    async def get_recording_settings(self, access_token: str) -> dict[str, Any]: ...


class ZoomRecordingSettingsClient:
    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self.http_client = http_client

    async def get_recording_settings(self, access_token: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"option": "recording"}
        if self.http_client is not None:
            response = await self.http_client.get(ZOOM_USER_SETTINGS_URL, headers=headers, params=params)
        else:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(ZOOM_USER_SETTINGS_URL, headers=headers, params=params)
        response.raise_for_status()
        return response.json()


class ZoomSettingsCheckService:
    def __init__(self, session: Session, client: ZoomRecordingSettingsClientProtocol | None = None) -> None:
        self.zoom_tokens = ZoomTokenRepository(session)
        self.client = client or ZoomRecordingSettingsClient()

    async def check_for_user(self, user_id: int) -> ZoomSettingsCheckResult:
        token = self.zoom_tokens.get_for_user(user_id)
        if token is None:
            return ZoomSettingsCheckResult(
                zoom_connected=False,
                paid_plan_or_cloud_access=None,
                cloud_recording_enabled=None,
                audio_transcription_enabled=None,
            )

        settings = await self.client.get_recording_settings(token.access_token)
        recording_settings = settings.get("recording") or settings
        return ZoomSettingsCheckResult(
            zoom_connected=True,
            paid_plan_or_cloud_access=None,
            cloud_recording_enabled=_bool_setting(recording_settings, "cloud_recording"),
            audio_transcription_enabled=_bool_setting(
                recording_settings,
                "recording_audio_transcript",
                "audio_transcript",
                "audio_transcription",
                "create_audio_transcript",
            ),
        )


def _bool_setting(settings: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        value = settings.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"true", "1", "yes", "on"}
        if value is not None:
            return bool(value)
    return False
