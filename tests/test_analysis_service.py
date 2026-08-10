import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.analysis.service import AnalysisService
from app.core.config import Settings
from app.db.base import Base
from app.models import LearningProfile, LearningProfileMember, Lesson, LessonAnalysis, Student, User, VocabularyCard
from app.schemas.cards import CardImageCandidate


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
    return Settings(app_env="test", openai_model="gpt-test-model", openverse_images_enabled=False)


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
    assert analysis.prompt_version == "lesson-analysis-v3"
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


async def test_analysis_prompt_addresses_group_collectively_without_singular_you():
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
    anna = Student(teacher_user_id=teacher.id, name="Анна", telegram_user_id=3001, invite_status="used")
    maria = Student(teacher_user_id=teacher.id, name="Мария", telegram_user_id=3002, invite_status="used")
    session.add_all([profile, anna, maria])
    session.flush()
    session.add_all([
        LearningProfileMember(learning_profile_id=profile.id, student_id=anna.id),
        LearningProfileMember(learning_profile_id=profile.id, student_id=maria.id),
    ])
    lesson = Lesson(
        teacher_user_id=teacher.id,
        learning_profile_id=profile.id,
        meeting_id="group-analysis",
        meeting_uuid="uuid-group-analysis",
        transcript="Teacher: What did you do yesterday? Students: We went to a museum.",
        processing_status="transcript_ready",
    )
    session.add(lesson)
    session.commit()
    llm = FakeLLMClient([valid_analysis_json()])

    await AnalysisService(session=session, settings=make_settings(), llm_client=llm).analyze_lesson(lesson.id)

    prompt = llm.prompts[0]
    assert "Profile type: group" in prompt
    assert "Profile name: Speaking B1" in prompt
    assert "Group members: Анна, Мария" in prompt
    assert "use plural/collective Russian address" in prompt
    assert "Do not use singular Russian ты/тебе/твой/твоя/твоё/твои" in prompt
    assert "Do not create per-student feedback" in prompt


async def test_analysis_prompt_allows_personal_address_for_individual_profile():
    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    profile = LearningProfile(
        teacher_user_id=teacher.id,
        name="Аня",
        profile_type="individual",
        card_publish_mode="manual_review",
    )
    student = Student(teacher_user_id=teacher.id, name="Аня", telegram_user_id=3001, invite_status="used")
    session.add_all([profile, student])
    session.flush()
    session.add(LearningProfileMember(learning_profile_id=profile.id, student_id=student.id))
    lesson = Lesson(
        teacher_user_id=teacher.id,
        learning_profile_id=profile.id,
        meeting_id="individual-analysis",
        meeting_uuid="uuid-individual-analysis",
        transcript="Teacher: What did you do yesterday? Student: I went to a museum.",
        processing_status="transcript_ready",
    )
    session.add(lesson)
    session.commit()
    llm = FakeLLMClient([valid_analysis_json()])

    await AnalysisService(session=session, settings=make_settings(), llm_client=llm).analyze_lesson(lesson.id)

    prompt = llm.prompts[0]
    assert "Profile type: individual" in prompt
    assert "Profile name: Аня" in prompt
    assert "Student name: Аня" in prompt
    assert "you may use singular Russian ты/тебе/твой" in prompt


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


class ConcurrentFakeImageClient:
    def __init__(self, failing_terms: set[str] | None = None, session: Session | None = None) -> None:
        self.failing_terms = failing_terms or set()
        self.session = session
        self.queries: list[str] = []
        self.active = 0
        self.max_active = 0

    async def search(self, query: str, offset: int = 0, limit: int = 3):
        import asyncio

        if self.session is not None:
            assert not self.session.in_transaction(), "DB transaction must not remain open during external await"
        self.queries.append(query)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0)
        self.active -= 1
        term = query.split()[0]
        if term in self.failing_terms:
            raise RuntimeError("candidate lookup failed")
        return [
            CardImageCandidate(
                image_id=f"image-{term}",
                image_url=f"https://images.test/{term}.jpg",
                source_url=f"https://source.test/{term}",
                creator="Creator",
                license="by",
                license_url="https://creativecommons.org/licenses/by/4.0/",
            )
        ]

    async def get(self, image_id: str):
        raise AssertionError("get should not be called")


async def test_analysis_enriches_only_new_cards_with_limited_concurrency_and_isolated_failure():
    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    profile = LearningProfile(
        teacher_user_id=teacher.id,
        name="B1",
        profile_type="group",
        card_publish_mode="manual_review",
    )
    session.add(profile)
    session.flush()
    old_card = VocabularyCard(
        teacher_user_id=teacher.id,
        learning_profile_id=profile.id,
        term="existing",
        translation_ru="старый",
        status="draft",
    )
    lesson = Lesson(
        teacher_user_id=teacher.id,
        learning_profile_id=profile.id,
        meeting_id="batch",
        meeting_uuid="uuid-batch",
        transcript="lesson transcript",
        processing_status="transcript_ready",
    )
    session.add_all([old_card, lesson])
    session.commit()
    analysis_payload = json.loads(valid_analysis_json())
    analysis_payload["vocabulary_cards"] = [
        {"term": term, "translation_ru": translation, "definition_en": f"Definition for {term}"}
        for term, translation in [("apple", "яблоко"), ("banana", "банан"), ("cherry", "вишня")]
    ]
    fake = ConcurrentFakeImageClient(failing_terms={"banana"}, session=session)
    settings = Settings(
        app_env="test",
        openai_model="gpt-test-model",
        openverse_images_enabled=True,
        openverse_batch_concurrency=2,
    )

    await AnalysisService(
        session=session,
        settings=settings,
        llm_client=FakeLLMClient([json.dumps(analysis_payload)]),
        image_client=fake,
    ).analyze_lesson(lesson.id)

    cards = {card.term: card for card in session.query(VocabularyCard).all()}
    assert fake.max_active == 2
    assert set(fake.queries) == {
        "apple",
        "banana",
        "cherry",
    }
    assert cards["apple"].image_url == "https://images.test/apple.jpg"
    assert cards["cherry"].image_url == "https://images.test/cherry.jpg"
    assert cards["banana"].image_url is None
    assert cards["banana"].image_search_query == "banana"
    assert cards["existing"].image_search_query is None
    assert session.get(Lesson, lesson.id).processing_status == "analyzed"
    assert session.query(LessonAnalysis).filter_by(lesson_id=lesson.id).count() == 1


async def test_analysis_survives_optional_image_commit_failure_and_rolls_back(monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    profile = LearningProfile(
        teacher_user_id=teacher.id,
        name="B1",
        profile_type="group",
        card_publish_mode="manual_review",
    )
    session.add(profile)
    session.flush()
    lesson = Lesson(
        teacher_user_id=teacher.id,
        learning_profile_id=profile.id,
        meeting_id="optional-db-failure",
        meeting_uuid="uuid-optional-db-failure",
        transcript="lesson transcript",
        processing_status="transcript_ready",
    )
    session.add(lesson)
    session.commit()
    real_commit = session.commit
    real_rollback = session.rollback
    commit_calls = 0
    rollback_calls = 0

    def flaky_commit():
        nonlocal commit_calls
        commit_calls += 1
        if commit_calls == 2:
            raise SQLAlchemyError("optional metadata commit failed")
        real_commit()

    def tracked_rollback():
        nonlocal rollback_calls
        rollback_calls += 1
        real_rollback()

    monkeypatch.setattr(session, "commit", flaky_commit)
    monkeypatch.setattr(session, "rollback", tracked_rollback)
    analysis = await AnalysisService(
        session=session,
        settings=Settings(app_env="test", openai_model="gpt-test-model", openverse_images_enabled=True),
        llm_client=FakeLLMClient([valid_analysis_json()]),
        image_client=ConcurrentFakeImageClient(session=session),
    ).analyze_lesson(lesson.id)

    assert analysis.lesson_id == lesson.id
    assert rollback_calls == 1
    assert session.get(Lesson, lesson.id).processing_status == "analyzed"
    assert session.query(LessonAnalysis).filter_by(lesson_id=lesson.id).count() == 1
    assert session.query(VocabularyCard).filter_by(lesson_id=lesson.id).count() == 1
