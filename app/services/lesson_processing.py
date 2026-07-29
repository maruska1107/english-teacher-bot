from sqlalchemy.orm import Session

from app.analysis.service import AnalysisService, LLMJsonClient
from app.core.config import Settings
from app.models import Lesson
from app.repositories.zoom_tokens import ZoomTokenRepository
from app.telegram.notifier import TelegramBotNotifier, TelegramNotifierProtocol
from app.zoom.transcripts import TranscriptClientProtocol, ZoomTranscriptClient


class LessonProcessingService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        transcript_client: TranscriptClientProtocol | None = None,
        llm_client: LLMJsonClient | None = None,
        notifier: TelegramNotifierProtocol | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.transcript_client = transcript_client or ZoomTranscriptClient()
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
            await self._notifier().send_message(
                lesson.teacher.telegram_user_id,
                self._teacher_message(analysis.teacher_report),
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
        lesson.transcript = await self.transcript_client.download_transcript(
            lesson.transcript_download_url,
            token.access_token,
        )
        lesson.processing_status = "transcript_ready"
        self.session.commit()

    def _clear_processed_source_data(self, lesson: Lesson) -> None:
        lesson.transcript = None
        lesson.transcript_download_url = None

    def _notifier(self) -> TelegramNotifierProtocol:
        if self.notifier is None:
            self.notifier = TelegramBotNotifier(self.settings)
        return self.notifier

    def _teacher_message(self, teacher_report: str) -> str:
        return f"Отчёт по уроку готов\n\n{teacher_report}"
