from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models import Lesson
from app.repositories.webhook_events import ProcessedWebhookEventRepository
from app.repositories.zoom_meeting_subscriptions import ZoomMeetingSubscriptionRepository
from app.repositories.zoom_tokens import ZoomTokenRepository


@dataclass(frozen=True)
class RecordingCompletedResult:
    status: str
    lesson: Lesson | None = None
    download_token: str | None = None


class ZoomWebhookService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = ProcessedWebhookEventRepository(session)
        self.zoom_meeting_subscriptions = ZoomMeetingSubscriptionRepository(session)
        self.zoom_tokens = ZoomTokenRepository(session)

    def handle_recording_completed(self, payload: dict[str, Any]) -> RecordingCompletedResult:
        event_id = self._event_id(payload)
        event_type = str(payload.get("event") or "recording.completed")
        if self.events.get(event_id) is not None:
            return RecordingCompletedResult(status="already_processed")

        event_payload = payload.get("payload") or {}
        meeting = event_payload.get("object") or {}
        zoom_account_id = event_payload.get("account_id")
        zoom_host_id = meeting.get("host_id")
        if not zoom_host_id:
            self.events.create(event_id=event_id, event_type=event_type, status="ignored_no_host")
            self.session.commit()
            return RecordingCompletedResult(status="ignored_no_host")
        teacher_user_id = self.zoom_tokens.find_teacher_id_for_zoom_host(
            zoom_user_id=str(zoom_host_id),
            zoom_account_id=zoom_account_id,
        )
        if teacher_user_id is None:
            self.events.create(event_id=event_id, event_type=event_type, status="ignored_no_teacher")
            self.session.commit()
            return RecordingCompletedResult(status="ignored_no_teacher")

        meeting_id = str(meeting.get("id") or "")
        subscription = self.zoom_meeting_subscriptions.active_for_user_and_meeting(
            user_id=teacher_user_id,
            meeting_id=meeting_id,
        )
        if subscription is None:
            self.events.create(
                event_id=event_id,
                event_type=event_type,
                status="ignored_unsubscribed_meeting",
            )
            self.session.commit()
            return RecordingCompletedResult(status="ignored_unsubscribed_meeting")

        transcript_download_url = self._transcript_download_url(meeting)
        if transcript_download_url is None:
            self.events.create(
                event_id=event_id,
                event_type=event_type,
                status="ignored_no_transcript",
            )
            self.session.commit()
            return RecordingCompletedResult(status="ignored_no_transcript")

        download_token = self._download_token(event_payload, meeting)
        lesson = Lesson(
            teacher_user_id=teacher_user_id,
            learning_profile_id=subscription.learning_profile_id,
            meeting_id=meeting_id,
            meeting_uuid=str(meeting.get("uuid") or ""),
            transcript_download_url=transcript_download_url,
            processing_status="pending",
        )
        self.session.add(lesson)
        self.events.create(event_id=event_id, event_type=event_type, status="accepted")
        self.session.commit()
        return RecordingCompletedResult(status="accepted", lesson=lesson, download_token=download_token)

    def _event_id(self, payload: dict[str, Any]) -> str:
        event = payload.get("event", "unknown")
        event_ts = payload.get("event_ts", "0")
        meeting_uuid = ((payload.get("payload") or {}).get("object") or {}).get("uuid") or "unknown"
        return f"{event}:{meeting_uuid}:{event_ts}"

    def _transcript_download_url(self, meeting: dict[str, Any]) -> str | None:
        if meeting.get("file_type") == "TRANSCRIPT" and meeting.get("download_url"):
            return meeting.get("download_url")
        recording_file = meeting.get("recording_file") or {}
        if recording_file.get("file_type") == "TRANSCRIPT" and recording_file.get("download_url"):
            return recording_file.get("download_url")
        for recording_file in meeting.get("recording_files") or []:
            if recording_file.get("file_type") == "TRANSCRIPT":
                return recording_file.get("download_url")
        return None

    def _download_token(self, event_payload: dict[str, Any], meeting: dict[str, Any]) -> str | None:
        token = event_payload.get("download_token") or meeting.get("download_token")
        if token:
            return str(token)
        recording_file = meeting.get("recording_file") or {}
        token = recording_file.get("download_token")
        if token:
            return str(token)
        for recording_file in meeting.get("recording_files") or []:
            if recording_file.get("file_type") == "TRANSCRIPT" and recording_file.get("download_token"):
                return str(recording_file["download_token"])
        return None
