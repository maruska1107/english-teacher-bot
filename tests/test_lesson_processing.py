import json
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.models import Lesson, User, ZoomToken
from app.services.lesson_processing import LessonProcessingService


class FakeTranscriptClient:
    async def download_transcript(self, download_url: str, access_token: str) -> str:
        assert download_url == "https://zoom.example/transcript.vtt"
        assert access_token == "access"
        return "Teacher: What did you do yesterday? Student: I go to London yesterday."


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
                "homework": ["Write 5 Past Simple sentences"],
                "teacher_recommendations": ["Review irregular verbs"],
                "student_message": "Сегодня мы потренировали Past Simple. Домашнее задание: 5 предложений.",
            }
        )


class FakeTelegramNotifier:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))


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
            expires_at=datetime(2026, 1, 1, tzinfo=UTC),
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
        transcript_client=FakeTranscriptClient(),
        llm_client=FakeLLMClient(),
        notifier=notifier,
    )

    await service.process_lesson(lesson.id)

    processed_lesson = session.get(Lesson, lesson.id)
    assert processed_lesson.transcript.startswith("Teacher: What did you do")
    assert processed_lesson.processing_status == "completed"
    assert processed_lesson.analysis is not None
    assert notifier.messages[0][0] == 1001
    assert "Отчёт по уроку" in notifier.messages[0][1]
    assert notifier.messages[1][0] == 9001
    assert "Скопирован отчёт по уроку" in notifier.messages[1][1]
