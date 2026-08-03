import hashlib
import hmac
import json
from urllib.parse import quote

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_app
from app.models import LearningProfile, LearningProfileMember, Student, StudentCardProgress, User, VocabularyCard


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory()


def make_settings() -> Settings:
    return Settings(app_env="test", telegram_bot_token="test-bot-token")


def signed_init_data(telegram_user_id: int, bot_token: str = "test-bot-token") -> str:
    fields = {
        "auth_date": "1780000000",
        "query_id": "student-cards-test",
        "user": json.dumps({"id": telegram_user_id, "first_name": "Student"}, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return "&".join(f"{key}={quote(value)}" for key, value in {**fields, "hash": signature}.items())


def make_client(session: Session) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = make_settings

    def override_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    return TestClient(app)


def seed_student_cards(session: Session) -> tuple[Student, VocabularyCard, VocabularyCard]:
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    student = Student(teacher_user_id=teacher.id, name="Анна", telegram_user_id=3003, invite_status="used")
    profile = LearningProfile(
        teacher_user_id=teacher.id,
        name="Анна",
        profile_type="individual",
        card_publish_mode="manual_review",
    )
    other_profile = LearningProfile(
        teacher_user_id=teacher.id,
        name="Other",
        profile_type="individual",
        card_publish_mode="manual_review",
    )
    session.add_all([student, profile, other_profile])
    session.flush()
    session.add(LearningProfileMember(learning_profile_id=profile.id, student_id=student.id))
    visible_card = VocabularyCard(
        teacher_user_id=teacher.id,
        learning_profile_id=profile.id,
        term="journey",
        translation_ru="путешествие",
        example_sentence="The journey was long.",
        status="published",
    )
    draft_card = VocabularyCard(
        teacher_user_id=teacher.id,
        learning_profile_id=profile.id,
        term="draft",
        translation_ru="черновик",
        status="draft",
    )
    other_card = VocabularyCard(
        teacher_user_id=teacher.id,
        learning_profile_id=other_profile.id,
        term="hidden",
        translation_ru="скрыто",
        status="published",
    )
    session.add_all([visible_card, draft_card, other_card])
    session.commit()
    return student, visible_card, draft_card


def test_student_can_list_only_published_cards_from_own_profiles():
    session = make_session()
    _, visible_card, _ = seed_student_cards(session)
    client = make_client(session)

    response = client.get("/api/student/cards", headers={"x-telegram-init-data": signed_init_data(3003)})

    assert response.status_code == 200
    assert response.json() == {
        "cards": [
            {
                "id": visible_card.id,
                "term": "journey",
                "translation_ru": "путешествие",
                "example_sentence": "The journey was long.",
                "status": "new",
                "image_url": None,
                "image_source_url": None,
                "image_creator": None,
                "image_license": None,
                "image_license_url": None,
                "image_search_query": None,
            }
        ]
    }


def test_student_card_list_serializes_populated_image_metadata():
    session = make_session()
    _, visible_card, _ = seed_student_cards(session)
    visible_card.image_url = "https://api.openverse.org/v1/images/openverse-1/thumb/"
    visible_card.image_source_url = "https://example.org/source"
    visible_card.image_creator = "Alice"
    visible_card.image_license = "by"
    visible_card.image_license_url = "https://creativecommons.org/licenses/by/4.0/"
    visible_card.image_search_query = "journey travel"
    session.commit()
    client = make_client(session)

    response = client.get("/api/student/cards", headers={"x-telegram-init-data": signed_init_data(3003)})

    assert response.status_code == 200
    assert response.json()["cards"][0] == {
        "id": visible_card.id,
        "term": "journey",
        "translation_ru": "путешествие",
        "example_sentence": "The journey was long.",
        "status": "new",
        "image_url": "https://api.openverse.org/v1/images/openverse-1/thumb/",
        "image_source_url": "https://example.org/source",
        "image_creator": "Alice",
        "image_license": "by",
        "image_license_url": "https://creativecommons.org/licenses/by/4.0/",
        "image_search_query": "journey travel",
    }


def test_student_can_update_card_progress():
    session = make_session()
    student, visible_card, _ = seed_student_cards(session)
    client = make_client(session)

    response = client.post(
        f"/api/student/cards/{visible_card.id}/progress",
        headers={"x-telegram-init-data": signed_init_data(3003)},
        json={"status": "known"},
    )

    assert response.status_code == 200
    assert response.json() == {"card_id": visible_card.id, "status": "known", "review_count": 1}
    progress = session.query(StudentCardProgress).filter_by(student_id=student.id, card_id=visible_card.id).one()
    assert progress.status == "known"
    assert progress.review_count == 1


def test_student_cards_api_rejects_unknown_student_and_draft_progress():
    session = make_session()
    _, _, draft_card = seed_student_cards(session)
    client = make_client(session)

    unknown = client.get("/api/student/cards", headers={"x-telegram-init-data": signed_init_data(9999)})
    draft = client.post(
        f"/api/student/cards/{draft_card.id}/progress",
        headers={"x-telegram-init-data": signed_init_data(3003)},
        json={"status": "known"},
    )

    assert unknown.status_code == 403
    assert draft.status_code == 404
