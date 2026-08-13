from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.analysis.service import AnalysisService, LLMJsonClient
from app.core.config import Settings
from app.models import Lesson, VocabularyCard
from app.repositories.zoom_tokens import ZoomTokenRepository
from app.telegram.messages import TEACHER_LESSON_READY_TEXT_TEMPLATE, TEACHER_LESSON_READY_WEBAPP_TEXT
from app.telegram.notifier import TelegramBotNotifier, TelegramNotifierProtocol
from app.zoom.oauth import ZoomOAuthClient, ZoomOAuthClientProtocol
from app.zoom.transcripts import TranscriptClientProtocol, ZoomTranscriptClient


class LessonProcessingService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        transcript_client: TranscriptClientProtocol | None = None,
        zoom_oauth_client: ZoomOAuthClientProtocol | None = None,
        llm_client: LLMJsonClient | None = None,
        notifier: TelegramNotifierProtocol | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.transcript_client = transcript_client or ZoomTranscriptClient()
        self.zoom_oauth_client = zoom_oauth_client or ZoomOAuthClient(settings)
        self.llm_client = llm_client
        self.notifier = notifier
        self.zoom_tokens = ZoomTokenRepository(session)

    async def process_lesson(self, lesson_id: int) -> Lesson:
        lesson = self.session.get(Lesson, lesson_id)
        if lesson is None:
            raise ValueError("Lesson not found")
        try:
            await self._download_transcript_if_needed(lesson)
            analysis = await AnalysisService(
                session=self.session,
                settings=self.settings,
                llm_client=self.llm_client,
            ).analyze_lesson(lesson.id)
            self._clear_processed_source_data(lesson)
            lesson.processing_status = "completed"
            self.session.commit()
            draft_card_count = self._draft_card_count(lesson.id)
            await self._notifier().send_message(
                lesson.teacher.telegram_user_id,
                self._teacher_message(analysis.teacher_report, draft_card_count),
            )
            await self._notifier().send_webapp_button(
                lesson.teacher.telegram_user_id,
                TEACHER_LESSON_READY_WEBAPP_TEXT,
                "Открыть На проверку",
                "https://englishtutorai.ru/teacher/cards",
            )
            if self.settings.telegram_admin_id is not None:
                await self._notifier().send_message(
                    self.settings.telegram_admin_id,
                    f"Скопирован отчёт по уроку teacher_user_id={lesson.teacher_user_id}\n\n{analysis.teacher_report}",
                )
            return lesson
        except Exception as exc:
            lesson.processing_status = "failed"
            lesson.processing_error = str(exc)
            self.session.commit()
            if self.settings.telegram_admin_id is not None:
                await self._notifier().send_message(
                    self.settings.telegram_admin_id,
                    f"Критическая ошибка обработки урока lesson_id={lesson.id}: {exc}",
                )
            raise

    async def _download_transcript_if_needed(self, lesson: Lesson) -> None:
        if lesson.transcript:
            return
        if not lesson.transcript_download_url:
            raise ValueError("Lesson transcript download URL is empty")
        token = self.zoom_tokens.get_for_user(lesson.teacher_user_id)
        if token is None:
            raise ValueError("Zoom token not found for lesson teacher")
        lesson.processing_status = "downloading_transcript"
        self.session.commit()
        access_token = await self._valid_zoom_access_token(token)
        lesson.transcript = await self.transcript_client.download_transcript(
            lesson.transcript_download_url,
            access_token,
        )
        lesson.processing_status = "transcript_ready"
        self.session.commit()

    async def _valid_zoom_access_token(self, token) -> str:
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        refresh_deadline = datetime.now(UTC) + timedelta(minutes=2)
        if expires_at > refresh_deadline:
            return token.access_token

        refreshed = await self.zoom_oauth_client.refresh_access_token(token.refresh_token)
        token.access_token = refreshed.access_token
        token.refresh_token = refreshed.refresh_token
        token.expires_at = datetime.now(UTC) + timedelta(seconds=refreshed.expires_in)
        self.session.commit()
        return token.access_token

    def _clear_processed_source_data(self, lesson: Lesson) -> None:
        lesson.transcript = None
        lesson.transcript_download_url = None

    def _notifier(self) -> TelegramNotifierProtocol:
        if self.notifier is None:
            self.notifier = TelegramBotNotifier(self.settings)
        return self.notifier

    def _draft_card_count(self, lesson_id: int) -> int:
        return self.session.query(VocabularyCard).filter_by(lesson_id=lesson_id, status="draft").count()

    def _teacher_message(self, teacher_report: str, draft_card_count: int = 0) -> str:
        return TEACHER_LESSON_READY_TEXT_TEMPLATE.format(card_count=draft_card_count)
