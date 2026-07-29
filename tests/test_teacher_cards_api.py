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
from app.models import LearningProfile, User, VocabularyCard


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
    return Settings(
        app_env="test",
        telegram_bot_token="test-bot-token",
        allowed_telegram_teacher_ids="1001",
    )


def signed_init_data(telegram_user_id: int, bot_token: str = "test-bot-token") -> str:
    fields = {
        "auth_date": "1780000000",
        "query_id": "teacher-cards-test",
        "user": json.dumps(
            {"id": telegram_user_id, "first_name": "Teacher", "username": "teacher"},
            separators=(",", ":"),
        ),
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


def seed_teacher_profile_and_cards(session: Session) -> tuple[User, LearningProfile, VocabularyCard, VocabularyCard]:
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
    draft_card = VocabularyCard(
        teacher_user_id=teacher.id,
        learning_profile_id=profile.id,
        term="journey",
        translation_ru="путешествие",
        definition_en="An act of travelling.",
        example_sentence="The journey was long.",
        source_phrase="journey",
        level="B1",
        status="draft",
    )
    published_card = VocabularyCard(
        teacher_user_id=teacher.id,
        learning_profile_id=profile.id,
        term="ticket",
        translation_ru="билет",
        status="published",
    )
    session.add_all([draft_card, published_card])
    session.commit()
    return teacher, profile, draft_card, published_card


def test_teacher_can_list_draft_cards_for_profile():
    session = make_session()
    _, profile, draft_card, _ = seed_teacher_profile_and_cards(session)
    client = make_client(session)

    response = client.get(
        f"/api/teacher/cards?profile_id={profile.id}&status=draft",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )

    assert response.status_code == 200
    assert response.json() == {
        "cards": [
            {
                "id": draft_card.id,
                "learning_profile_id": profile.id,
                "term": "journey",
                "translation_ru": "путешествие",
                "definition_en": "An act of travelling.",
                "example_sentence": "The journey was long.",
                "source_phrase": "journey",
                "level": "B1",
                "status": "draft",
            }
        ]
    }


def test_teacher_can_update_publish_and_archive_own_card():
    session = make_session()
    _, _, draft_card, _ = seed_teacher_profile_and_cards(session)
    client = make_client(session)
    headers = {"x-telegram-init-data": signed_init_data(1001)}

    update_response = client.patch(
        f"/api/teacher/cards/{draft_card.id}",
        headers=headers,
        json={
            "term": "make a journey",
            "translation_ru": "совершить путешествие",
            "definition_en": "To travel somewhere.",
            "example_sentence": "We made a journey to London.",
            "source_phrase": "journey",
            "level": "B1",
        },
    )
    publish_response = client.post(f"/api/teacher/cards/{draft_card.id}/publish", headers=headers)
    archive_response = client.post(f"/api/teacher/cards/{draft_card.id}/archive", headers=headers)

    assert update_response.status_code == 200
    assert update_response.json()["term"] == "make a journey"
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "published"
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"


def test_teacher_cards_api_rejects_invalid_init_data_and_other_teacher_card():
    session = make_session()
    _, _, draft_card, _ = seed_teacher_profile_and_cards(session)
    other_teacher = User(telegram_user_id=2002, role="teacher", is_active=True)
    session.add(other_teacher)
    session.commit()
    client = make_client(session)

    bad_auth = client.get("/api/teacher/cards", headers={"x-telegram-init-data": "bad=data"})
    not_allowed = client.get("/api/teacher/cards", headers={"x-telegram-init-data": signed_init_data(2002)})
    other_card = client.patch(
        f"/api/teacher/cards/{draft_card.id}",
        headers={"x-telegram-init-data": signed_init_data(2002)},
        json={"term": "stolen"},
    )

    assert bad_auth.status_code == 401
    assert not_allowed.status_code == 403
    assert other_card.status_code == 403
