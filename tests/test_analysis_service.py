import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.analysis.service import AnalysisService
from app.core.config import Settings
from app.db.base import Base
from app.models import LearningProfile, Lesson, LessonAnalysis, User, VocabularyCard


class FakeLLMClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.prompts: list[str] = []

    async def complete_json(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory()


def make_settings() -> Settings:
    return Settings(app_env="test", openai_model="gpt-test-model")


def valid_analysis_json() -> str:
    return json.dumps(
        {
            "summary": "Ученики практиковали past simple в диалогах о путешествиях.",
            "strengths": ["Хорошая вовлечённость", "Понятные ответы на вопросы"],
            "mistakes": [
                {
                    "quote": "I go to London yesterday",
                    "correction": "I went to London yesterday",
                    "explanation": "После yesterday нужен Past Simple.",
                }
            ],
            "vocabulary": ["journey", "ticket"],
            "vocabulary_cards": [
                {
                    "term": "journey",
                    "translation_ru": "путешествие",
                    "definition_en": "An act of travelling from one place to another.",
                    "example_sentence": "The journey took three hours.",
                    "source_phrase": "journey",
                    "level": "B1",
                }
            ],
            "homework": ["Написать 5 предложений в Past Simple"],
            "teacher_recommendations": ["Дать больше controlled practice"],
            "student_message": "Сегодня мы потренировали Past Simple. Домашнее задание: 5 предложений.",
        }
    )


async def test_analysis_service_retries_once_after_invalid_json_and_saves_analysis():
    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    lesson = Lesson(
        teacher_user_id=teacher.id,
        meeting_id="1",
        meeting_uuid="uuid-1",
        transcript="Teacher: What did you do yesterday? Student: I go to London yesterday.",
        processing_status="transcript_ready",
    )
    session.add(lesson)
    session.commit()
    llm = FakeLLMClient(["not-json", valid_analysis_json()])
    service = AnalysisService(session=session, settings=make_settings(), llm_client=llm)

    analysis = await service.analyze_lesson(lesson.id)

    assert len(llm.prompts) == 2
    assert analysis.lesson_id == lesson.id
    assert "Past Simple" in analysis.teacher_report
    assert "Сегодня мы потренировали" in analysis.student_message
    assert analysis.model == "gpt-test-model"
    assert analysis.prompt_version == "lesson-analysis-v2"
    assert session.get(Lesson, lesson.id).processing_status == "analyzed"
    assert session.query(LessonAnalysis).filter_by(lesson_id=lesson.id).count() == 1


async def test_analysis_service_creates_draft_vocabulary_cards_for_profile_lesson():
    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
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
        meeting_uuid="uuid-cards-1",
        transcript="Teacher: Let's plan a journey. Student: The journey was long.",
        processing_status="transcript_ready",
    )
    session.add(lesson)
    session.commit()
    service = AnalysisService(
        session=session,
        settings=make_settings(),
        llm_client=FakeLLMClient([valid_analysis_json()]),
    )

    analysis = await service.analyze_lesson(lesson.id)

    cards = session.query(VocabularyCard).filter_by(lesson_id=lesson.id).all()
    assert len(cards) == 1
    assert cards[0].teacher_user_id == teacher.id
    assert cards[0].learning_profile_id == profile.id
    assert cards[0].term == "journey"
    assert cards[0].translation_ru == "путешествие"
    assert cards[0].status == "draft"
    assert analysis.analysis_json["vocabulary_cards"][0]["term"] == "journey"


async def test_analysis_service_marks_lesson_failed_after_invalid_retry():
    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    lesson = Lesson(
        teacher_user_id=teacher.id,
        meeting_id="1",
        meeting_uuid="uuid-1",
        transcript="short transcript",
        processing_status="transcript_ready",
    )
    session.add(lesson)
    session.commit()
    service = AnalysisService(session=session, settings=make_settings(), llm_client=FakeLLMClient(["bad", "still bad"]))

    try:
        await service.analyze_lesson(lesson.id)
    except ValueError as exc:
        assert "valid JSON" in str(exc)
    else:
        raise AssertionError("Expected invalid LLM response to raise ValueError")

    failed_lesson = session.get(Lesson, lesson.id)
    assert failed_lesson.processing_status == "failed"
    assert "valid JSON" in failed_lesson.processing_error
