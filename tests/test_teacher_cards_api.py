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
from app.schemas.cards import CardImageCandidate
from app.services.openverse_images import get_openverse_image_client


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
        openverse_images_enabled=False,
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
                "image_url": None,
                "image_source_url": None,
                "image_creator": None,
                "image_license": None,
                "image_license_url": None,
                "image_search_query": None,
            }
        ]
    }


def test_teacher_card_list_serializes_populated_image_metadata():
    session = make_session()
    _, profile, draft_card, _ = seed_teacher_profile_and_cards(session)
    draft_card.image_url = "https://api.openverse.org/v1/images/openverse-1/thumb/"
    draft_card.image_source_url = "https://example.org/source"
    draft_card.image_creator = "Alice"
    draft_card.image_license = "by"
    draft_card.image_license_url = "https://creativecommons.org/licenses/by/4.0/"
    draft_card.image_search_query = "journey travel"
    session.commit()
    client = make_client(session)

    response = client.get(
        f"/api/teacher/cards?profile_id={profile.id}&status=draft",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )

    assert response.status_code == 200
    assert response.json()["cards"][0] == {
        "id": draft_card.id,
        "learning_profile_id": profile.id,
        "term": "journey",
        "translation_ru": "путешествие",
        "definition_en": "An act of travelling.",
        "example_sentence": "The journey was long.",
        "source_phrase": "journey",
        "level": "B1",
        "status": "draft",
        "image_url": "https://api.openverse.org/v1/images/openverse-1/thumb/",
        "image_source_url": "https://example.org/source",
        "image_creator": "Alice",
        "image_license": "by",
        "image_license_url": "https://creativecommons.org/licenses/by/4.0/",
        "image_search_query": "journey travel",
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


def test_teacher_profile_repository_counts_new_and_published_cards():
    session = make_session()
    teacher, profile, _, _ = seed_teacher_profile_and_cards(session)
    other_profile = LearningProfile(
        teacher_user_id=teacher.id,
        name="Анна",
        profile_type="individual",
        card_publish_mode="manual_review",
    )
    session.add(other_profile)
    session.flush()
    session.add(
        VocabularyCard(
            teacher_user_id=teacher.id,
            learning_profile_id=other_profile.id,
            term="apple",
            translation_ru="яблоко",
            status="draft",
        )
    )
    session.commit()

    from app.repositories.learning_profiles import LearningProfileRepository

    rows = LearningProfileRepository(session).list_with_card_counts(teacher.id)

    assert [(row[0].name, row[1], row[2]) for row in rows] == [
        ("Speaking B1", 1, 1),
        ("Анна", 1, 0),
    ]


def test_vocabulary_repository_can_create_delete_and_batch_publish_cards():
    session = make_session()
    teacher, profile, draft_card, published_card = seed_teacher_profile_and_cards(session)

    from app.repositories.vocabulary_cards import VocabularyCardRepository
    from app.schemas.cards import VocabularyCardCreate

    repository = VocabularyCardRepository(session)
    manual_card = repository.create_manual_draft_card(
        teacher_user_id=teacher.id,
        payload=VocabularyCardCreate(
            learning_profile_id=profile.id,
            term="fluency",
            translation_ru="беглость речи",
            definition_en="speaking smoothly",
            example_sentence="Her fluency improved.",
            source_phrase=None,
            level="B1",
        ),
    )
    session.commit()

    assert manual_card.status == "draft"
    assert manual_card.learning_profile_id == profile.id

    repository.delete_card(published_card)
    published_count = repository.publish_draft_cards_for_profile(teacher.id, profile.id)
    session.commit()

    assert published_count == 2
    assert session.get(VocabularyCard, published_card.id) is None
    assert session.get(VocabularyCard, draft_card.id).status == "published"
    assert session.get(VocabularyCard, manual_card.id).status == "published"


def test_vocabulary_repository_can_set_and_clear_image_metadata():
    session = make_session()
    _, _, draft_card, _ = seed_teacher_profile_and_cards(session)

    from app.repositories.vocabulary_cards import VocabularyCardRepository
    from app.schemas.cards import CardImageCandidate

    repository = VocabularyCardRepository(session)
    candidate = CardImageCandidate(
        image_id="openverse-1",
        image_url="https://api.openverse.org/v1/images/openverse-1/thumb/",
        source_url="https://example.org/source",
        creator="Alice",
        license="by",
        license_url="https://creativecommons.org/licenses/by/4.0/",
    )

    repository.set_image(draft_card, candidate, "journey travel")

    assert draft_card.image_url == candidate.image_url
    assert draft_card.image_source_url == candidate.source_url
    assert draft_card.image_creator == "Alice"
    assert draft_card.image_license == "by"
    assert draft_card.image_license_url == candidate.license_url
    assert draft_card.image_search_query == "journey travel"

    repository.clear_image(draft_card)

    assert draft_card.image_url is None
    assert draft_card.image_source_url is None
    assert draft_card.image_creator is None
    assert draft_card.image_license is None
    assert draft_card.image_license_url is None
    assert draft_card.image_search_query == "journey travel"


def test_card_image_selection_validates_image_id_length():
    from pydantic import ValidationError

    from app.schemas.cards import CardImageSelection

    CardImageSelection(image_id="openverse-1")
    for invalid_image_id in ("", "x" * 101):
        try:
            CardImageSelection(image_id=invalid_image_id)
        except ValidationError:
            continue
        raise AssertionError("invalid image_id was accepted")


def test_teacher_can_list_card_profiles_with_counts():
    session = make_session()
    _, profile, _, _ = seed_teacher_profile_and_cards(session)
    client = make_client(session)

    response = client.get(
        "/api/teacher/card-profiles",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )

    assert response.status_code == 200
    assert response.json() == {
        "profiles": [
            {
                "id": profile.id,
                "name": "Speaking B1",
                "profile_type": "group",
                "new_card_count": 1,
                "published_card_count": 1,
            }
        ]
    }


def test_teacher_can_create_delete_and_batch_publish_cards_via_api():
    session = make_session()
    _, profile, draft_card, published_card = seed_teacher_profile_and_cards(session)
    client = make_client(session)
    headers = {"x-telegram-init-data": signed_init_data(1001)}

    create_response = client.post(
        "/api/teacher/cards",
        headers=headers,
        json={
            "learning_profile_id": profile.id,
            "term": "fluency",
            "translation_ru": "беглость речи",
            "definition_en": "speaking smoothly",
            "example_sentence": "Her fluency improved.",
            "source_phrase": None,
            "level": "B1",
        },
    )
    delete_response = client.delete(f"/api/teacher/cards/{published_card.id}", headers=headers)
    publish_response = client.post(
        "/api/teacher/cards/publish-batch",
        headers=headers,
        json={"learning_profile_id": profile.id},
    )

    assert create_response.status_code == 200
    assert create_response.json()["status"] == "draft"
    assert delete_response.status_code == 204
    assert session.get(VocabularyCard, published_card.id) is None
    assert publish_response.status_code == 200
    assert publish_response.json() == {"published_count": 2}
    assert session.get(VocabularyCard, draft_card.id).status == "published"
    assert session.get(VocabularyCard, create_response.json()["id"]).status == "published"


def test_teacher_cannot_create_card_for_other_teacher_profile_or_batch_publish_it():
    session = make_session()
    _, profile, _, _ = seed_teacher_profile_and_cards(session)
    other_teacher = User(telegram_user_id=2002, role="teacher", is_active=True)
    session.add(other_teacher)
    session.flush()
    other_profile = LearningProfile(
        teacher_user_id=other_teacher.id,
        name="Other",
        profile_type="individual",
        card_publish_mode="manual_review",
    )
    session.add(other_profile)
    session.commit()
    client = make_client(session)
    headers = {"x-telegram-init-data": signed_init_data(1001)}

    create_other = client.post(
        "/api/teacher/cards",
        headers=headers,
        json={
            "learning_profile_id": other_profile.id,
            "term": "bad",
            "translation_ru": "плохо",
        },
    )
    publish_other = client.post(
        "/api/teacher/cards/publish-batch",
        headers=headers,
        json={"learning_profile_id": other_profile.id},
    )
    publish_own = client.post(
        "/api/teacher/cards/publish-batch",
        headers=headers,
        json={"learning_profile_id": profile.id},
    )

    assert create_other.status_code == 404
    assert publish_other.status_code == 404
    assert publish_own.status_code == 200


class FakeCreateImageClient:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.queries: list[str] = []

    async def search(self, query: str, offset: int = 0, limit: int = 3):
        self.queries.append(query)
        if self.fail:
            raise RuntimeError("Openverse unavailable")
        return [
            CardImageCandidate(
                image_id="fluency-image",
                image_url="https://images.test/fluency.jpg",
                source_url="https://source.test/fluency",
                creator="Alice",
                license="by",
                license_url="https://creativecommons.org/licenses/by/4.0/",
            )
        ]

    async def get(self, image_id: str):
        raise AssertionError("get should not be called")


def test_manual_create_commits_draft_then_enriches_with_overridden_client():
    session = make_session()
    _, profile, _, _ = seed_teacher_profile_and_cards(session)
    client = make_client(session)
    fake = FakeCreateImageClient()
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="test",
        telegram_bot_token="test-bot-token",
        allowed_telegram_teacher_ids="1001",
        openverse_images_enabled=True,
    )
    client.app.dependency_overrides[get_openverse_image_client] = lambda: fake

    response = client.post(
        "/api/teacher/cards",
        headers={"x-telegram-init-data": signed_init_data(1001)},
        json={
            "learning_profile_id": profile.id,
            "term": "fluency",
            "translation_ru": "беглость",
            "definition_en": "speaking smoothly",
        },
    )

    assert response.status_code == 200
    assert response.json()["image_url"] == "https://images.test/fluency.jpg"
    assert fake.queries == ["fluency speaking smoothly"]
    assert session.get(VocabularyCard, response.json()["id"]).status == "draft"


def test_manual_create_returns_committed_draft_when_external_lookup_fails():
    session = make_session()
    _, profile, _, _ = seed_teacher_profile_and_cards(session)
    client = make_client(session)
    fake = FakeCreateImageClient(fail=True)
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="test",
        telegram_bot_token="test-bot-token",
        allowed_telegram_teacher_ids="1001",
        openverse_images_enabled=True,
    )
    client.app.dependency_overrides[get_openverse_image_client] = lambda: fake

    response = client.post(
        "/api/teacher/cards",
        headers={"x-telegram-init-data": signed_init_data(1001)},
        json={"learning_profile_id": profile.id, "term": "fluency", "translation_ru": "беглость"},
    )

    assert response.status_code == 200
    stored = session.get(VocabularyCard, response.json()["id"])
    assert stored.status == "draft"
    assert stored.image_url is None
    assert stored.image_search_query == "fluency"
