import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.models import LearningProfile, Lesson, User, ZoomToken
from app.services.lesson_processing import LessonProcessingService
from app.zoom.oauth import ZoomTokenPayload


class FakeTranscriptClient:
    async def download_transcript(
        self,
        download_url: str,
        access_token: str,
        download_token: str | None = None,
    ) -> str:
        assert download_url == "https://zoom.example/transcript.vtt"
        assert access_token == "access"
        assert download_token is None
        return "Teacher: What did you do yesterday? Student: I go to London yesterday."


class RecordingTranscriptClient:
    def __init__(self) -> None:
        self.access_tokens: list[str] = []
        self.download_tokens: list[str | None] = []

    async def download_transcript(
        self,
        download_url: str,
        access_token: str,
        download_token: str | None = None,
    ) -> str:
        self.access_tokens.append(access_token)
        self.download_tokens.append(download_token)
        return "Teacher: What did you do yesterday? Student: I go to London yesterday."


class FailingTranscriptClient:
    async def download_transcript(
        self,
        download_url: str,
        access_token: str,
        download_token: str | None = None,
    ) -> str:
        raise RuntimeError(f"Failed to download {download_url}?access_token=secret-token")


class FakeZoomOAuthClient:
    def __init__(self) -> None:
        self.refresh_tokens: list[str] = []

    async def exchange_code_for_token(self, code: str) -> ZoomTokenPayload:
        raise AssertionError("not used")

    async def refresh_access_token(self, refresh_token: str) -> ZoomTokenPayload:
        self.refresh_tokens.append(refresh_token)
        return ZoomTokenPayload(access_token="fresh-access", refresh_token="fresh-refresh", expires_in=3600)

    async def get_current_user(self, access_token: str):
        raise AssertionError("not used")


class FakeLLMClient:
    async def complete_json(self, prompt: str) -> str:
        return json.dumps(
            {
                "summary": "Past Simple practice.",
                "strengths": ["Good participation"],
                "mistakes": [
                    {
                        "quote": "I go to London yesterday",
                        "correction": "I went to London yesterday",
                        "explanation": "Use Past Simple with yesterday.",
                    }
                ],
                "vocabulary": ["travel"],
                "vocabulary_cards": [
                    {
                        "term": "travel",
                        "translation_ru": "путешествовать",
                        "definition_en": "To go from one place to another.",
                        "example_sentence": "I travel by train.",
                        "source_phrase": "travel",
                        "level": "A2",
                    }
                ],
                "homework": ["Write 5 Past Simple sentences"],
                "teacher_recommendations": ["Review irregular verbs"],
                "student_message": "Сегодня мы потренировали Past Simple. Домашнее задание: 5 предложений.",
            }
        )


class FakeTelegramNotifier:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []
        self.webapp_buttons: list[tuple[int, str, str, str]] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))

    async def send_webapp_button(self, chat_id: int, text: str, button_text: str, webapp_url: str) -> None:
        self.webapp_buttons.append((chat_id, text, button_text, webapp_url))


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory()


def make_settings() -> Settings:
    return Settings(app_env="test", telegram_admin_id=9001, openai_model="gpt-test-model")


async def test_process_pending_lesson_downloads_transcript_analyzes_and_notifies_teacher_and_admin():
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
            expires_at=datetime(2099, 1, 1, tzinfo=UTC),
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
    lesson = Lesson(
        teacher_user_id=teacher.id,
        learning_profile_id=profile.id,
        meeting_id="1",
        meeting_uuid="uuid-1",
        transcript_download_url="https://zoom.example/transcript.vtt",
        processing_status="pending",
    )
    session.add(lesson)
    session.commit()
    notifier = FakeTelegramNotifier()
    service = LessonProcessingService(
        session=session,
        settings=make_settings(),
        transcript_client=FakeTranscriptClient(),
        llm_client=FakeLLMClient(),
        notifier=notifier,
    )

    await service.process_lesson(lesson.id)

    processed_lesson = session.get(Lesson, lesson.id)
    assert processed_lesson.transcript is None
    assert processed_lesson.transcript_download_url is None
    assert processed_lesson.processing_status == "completed"
    assert processed_lesson.analysis is not None
    assert notifier.messages[0][0] == 1001
    assert "✨ Урок готов к проверке" in notifier.messages[0][1]
    assert "Новые карточки: 1" in notifier.messages[0][1]
    assert notifier.webapp_buttons == [
        (
            1001,
            "Откройте раздел «На проверку», проверьте итоги, домашку и карточки, "
            "а затем отправьте всё ученику.",
            "Открыть На проверку",
            "https://englishtutorai.ru/teacher/cards",
        )
    ]
    assert notifier.messages[1][0] == 9001
    assert "Скопирован отчёт по уроку" in notifier.messages[1][1]


async def test_process_lesson_refreshes_expired_zoom_access_token_before_downloading_transcript():
    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    token = ZoomToken(
        user_id=teacher.id,
        zoom_account_id="account-1",
        zoom_user_id="zoom-user-1",
        access_token="expired-access",
        refresh_token="old-refresh",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    session.add(token)
    lesson = Lesson(
        teacher_user_id=teacher.id,
        meeting_id="1",
        meeting_uuid="uuid-1",
        transcript_download_url="https://zoom.example/transcript.vtt",
        transcript="already downloaded transcript",
        processing_status="pending",
    )
    session.add(lesson)
    session.commit()
    transcript_client = RecordingTranscriptClient()
    zoom_oauth_client = FakeZoomOAuthClient()
    service = LessonProcessingService(
        session=session,
        settings=make_settings(),
        transcript_client=transcript_client,
        zoom_oauth_client=zoom_oauth_client,
        llm_client=FakeLLMClient(),
        notifier=FakeTelegramNotifier(),
    )

    lesson.transcript = None
    await service.process_lesson(lesson.id)

    assert zoom_oauth_client.refresh_tokens == ["old-refresh"]
    assert transcript_client.access_tokens == ["fresh-access"]
    assert transcript_client.download_tokens == [None]
    refreshed_token = session.get(ZoomToken, token.id)
    assert refreshed_token.access_token == "fresh-access"
    assert refreshed_token.refresh_token == "fresh-refresh"


async def test_process_lesson_passes_zoom_webhook_download_token_to_transcript_client():
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
            expires_at=datetime(2099, 1, 1, tzinfo=UTC),
        )
    )
    lesson = Lesson(
        teacher_user_id=teacher.id,
        meeting_id="1",
        meeting_uuid="uuid-1",
        transcript_download_url="https://zoom.example/transcript.vtt",
        processing_status="pending",
    )
    session.add(lesson)
    session.commit()
    transcript_client = RecordingTranscriptClient()
    service = LessonProcessingService(
        session=session,
        settings=make_settings(),
        transcript_client=transcript_client,
        llm_client=FakeLLMClient(),
        notifier=FakeTelegramNotifier(),
    )

    await service.process_lesson(lesson.id, zoom_download_token="webhook-download-token")

    assert transcript_client.access_tokens == ["access"]
    assert transcript_client.download_tokens == ["webhook-download-token"]


async def test_process_lesson_redacts_download_urls_in_admin_error_notification():
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
            expires_at=datetime(2099, 1, 1, tzinfo=UTC),
        )
    )
    lesson = Lesson(
        teacher_user_id=teacher.id,
        meeting_id="1",
        meeting_uuid="uuid-1",
        transcript_download_url="https://zoom.example/transcript.vtt",
        processing_status="pending",
    )
    session.add(lesson)
    session.commit()
    notifier = FakeTelegramNotifier()
    service = LessonProcessingService(
        session=session,
        settings=make_settings(),
        transcript_client=FailingTranscriptClient(),
        llm_client=FakeLLMClient(),
        notifier=notifier,
    )

    try:
        await service.process_lesson(lesson.id)
    except RuntimeError:
        pass

    assert notifier.messages[0][0] == 9001
    assert "[REDACTED_URL]" in notifier.messages[0][1]
    assert "https://zoom.example" not in notifier.messages[0][1]
    assert "secret-token" not in notifier.messages[0][1]
