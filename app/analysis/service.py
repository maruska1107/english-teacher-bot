import asyncio
import json
from typing import Protocol

from openai import AsyncOpenAI
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Lesson, LessonAnalysis, VocabularyCard
from app.prompts.lesson_analysis import LESSON_ANALYSIS_PROMPT_TEMPLATE, PROMPT_VERSION
from app.repositories.vocabulary_cards import VocabularyCardRepository
from app.schemas.analysis import LessonAnalysisResult
from app.services.openverse_images import (
    OpenverseImageClient,
    OpenverseImageClientProtocol,
    enrich_card_image,
)


class LLMJsonClient(Protocol):
    async def complete_json(self, prompt: str) -> str: ...


class OpenAIJsonClient:
    def __init__(self, settings: Settings) -> None:
        if settings.openai_api_key is None:
            raise RuntimeError("OpenAI API key is not configured")
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    async def complete_json(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an English lesson analyst. Return strictly valid JSON and no markdown.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return response.choices[0].message.content or ""


class AnalysisService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        llm_client: LLMJsonClient | None = None,
        image_client: OpenverseImageClientProtocol | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.llm_client = llm_client or OpenAIJsonClient(settings)
        self.image_client = image_client if image_client is not None else OpenverseImageClient(settings)

    async def analyze_lesson(self, lesson_id: int) -> LessonAnalysis:
        lesson = self.session.get(Lesson, lesson_id)
        if lesson is None:
            raise ValueError("Lesson not found")
        if not lesson.transcript:
            self._mark_failed(lesson, "Lesson transcript is empty")
            raise ValueError("Lesson transcript is empty")

        prompt = LESSON_ANALYSIS_PROMPT_TEMPLATE.format(transcript=lesson.transcript)
        last_error: Exception | None = None
        for _attempt in range(2):
            raw_response = await self.llm_client.complete_json(prompt)
            try:
                result = LessonAnalysisResult.model_validate(json.loads(raw_response))
                return await self._save_analysis(lesson, result)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc

        message = f"LLM did not return valid JSON: {last_error}"
        self._mark_failed(lesson, message)
        raise ValueError(message)

    async def _save_analysis(self, lesson: Lesson, result: LessonAnalysisResult) -> LessonAnalysis:
        teacher_report = self._build_teacher_report(result)
        existing = lesson.analysis
        if existing is None:
            analysis = LessonAnalysis(
                lesson_id=lesson.id,
                analysis_json=result.model_dump(mode="json"),
                teacher_report=teacher_report,
                student_message=result.student_message,
                model=self.settings.openai_model,
                prompt_version=PROMPT_VERSION,
            )
            self.session.add(analysis)
        else:
            analysis = existing
            analysis.analysis_json = result.model_dump(mode="json")
            analysis.teacher_report = teacher_report
            analysis.student_message = result.student_message
            analysis.model = self.settings.openai_model
            analysis.prompt_version = PROMPT_VERSION
        new_cards = self._save_draft_vocabulary_cards(lesson, result)
        lesson.processing_status = "analyzed"
        lesson.processing_error = None
        self.session.commit()
        await self._enrich_new_cards(new_cards)
        self.session.commit()
        return analysis

    def _save_draft_vocabulary_cards(
        self, lesson: Lesson, result: LessonAnalysisResult
    ) -> list[VocabularyCard]:
        if lesson.learning_profile_id is None or not result.vocabulary_cards:
            return []
        return VocabularyCardRepository(self.session).create_draft_cards(
            teacher_user_id=lesson.teacher_user_id,
            learning_profile_id=lesson.learning_profile_id,
            lesson_id=lesson.id,
            cards=[card.model_dump(mode="json") for card in result.vocabulary_cards],
        )

    async def _enrich_new_cards(self, cards: list[VocabularyCard]) -> None:
        if not cards or not self.settings.openverse_images_enabled:
            return
        semaphore = asyncio.Semaphore(max(1, self.settings.openverse_batch_concurrency))

        async def enrich(card: VocabularyCard) -> None:
            async with semaphore:
                await enrich_card_image(self.session, card, self.settings, self.image_client)

        await asyncio.gather(*(enrich(card) for card in cards))

    def _mark_failed(self, lesson: Lesson, message: str) -> None:
        lesson.processing_status = "failed"
        lesson.processing_error = message
        self.session.commit()

    def _build_teacher_report(self, result: LessonAnalysisResult) -> str:
        mistakes = (
            "\n".join(f"- {mistake.quote} → {mistake.correction}: {mistake.explanation}" for mistake in result.mistakes)
            or "- Нет явных ошибок в ответе модели."
        )
        return (
            "Отчёт по уроку\n\n"
            f"Кратко: {result.summary}\n\n"
            f"Сильные стороны:\n{self._bullet_list(result.strengths)}\n\n"
            f"Ошибки и коррекции:\n{mistakes}\n\n"
            f"Лексика:\n{self._bullet_list(result.vocabulary)}\n\n"
            f"Домашнее задание:\n{self._bullet_list(result.homework)}\n\n"
            f"Рекомендации преподавателю:\n{self._bullet_list(result.teacher_recommendations)}"
        )

    def _bullet_list(self, items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "- Нет данных"
