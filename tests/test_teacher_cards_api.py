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
from app.services.openverse_images import (
    OpenverseOperationResult,
    OpenverseOperationStatus,
    get_openverse_image_client,
)


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory()


def make_settings(**overrides) -> Settings:
    defaults = {
        "app_env": "test",
        "telegram_bot_token": "test-bot-token",
        "allowed_telegram_teacher_ids": "1001",
        "openverse_images_enabled": False,
    }
    defaults.update(overrides)
    return Settings(**defaults)


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


def make_client(session: Session, settings: Settings | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings or make_settings()

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


def test_zoom_review_mode_allows_existing_reviewer_teacher_to_use_own_teacher_cards_api():
    session = make_session()
    reviewer = User(telegram_user_id=2002, role="teacher", is_active=True)
    session.add(reviewer)
    session.flush()
    profile = LearningProfile(
        teacher_user_id=reviewer.id,
        name="Zoom Review",
        profile_type="individual",
        card_publish_mode="manual_review",
    )
    session.add(profile)
    session.commit()
    client = make_client(session, settings=make_settings(zoom_review_access_enabled=True))

    response = client.get(
        "/api/teacher/card-profiles",
        headers={"x-telegram-init-data": signed_init_data(2002)},
    )

    assert response.status_code == 200
    assert response.json()["profiles"][0]["name"] == "Zoom Review"


def test_zoom_review_mode_still_rejects_unknown_webapp_user_without_start_or_oauth():
    session = make_session()
    client = make_client(session, settings=make_settings(zoom_review_access_enabled=True))

    response = client.get(
        "/api/teacher/card-profiles",
        headers={"x-telegram-init-data": signed_init_data(2002)},
    )

    assert response.status_code == 403


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
    def __init__(self, fail: bool = False, session: Session | None = None) -> None:
        self.fail = fail
        self.session = session
        self.queries: list[str] = []

    async def search(self, query: str, offset: int = 0, limit: int = 3):
        if self.session is not None:
            assert not self.session.in_transaction(), "manual draft must commit before external lookup"
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


class FakeManageImageClient:
    def __init__(
        self,
        *,
        fail_search: bool = False,
        fail_get: bool = False,
        reject_get: bool = False,
        session: Session | None = None,
        during_search=None,
        during_get=None,
        search_pages: dict[int, list[CardImageCandidate]] | None = None,
    ) -> None:
        self.fail_search = fail_search
        self.fail_get = fail_get
        self.reject_get = reject_get
        self.search_calls: list[tuple[str, int, int]] = []
        self.get_calls: list[str] = []
        self.session = session
        self.during_search = during_search
        self.during_get = during_get
        self.search_pages = search_pages

    async def search(self, query: str, offset: int = 0, limit: int = 3):
        self.search_calls.append((query, offset, limit))
        if self.fail_search:
            raise RuntimeError("secret provider detail")
        return [
            CardImageCandidate(
                image_id=f"image-{offset + index}",
                image_url=f"https://images.test/{offset + index}.jpg",
                source_url=f"https://source.test/{offset + index}",
                creator=f"Creator {index}",
                license="by",
                license_url="https://creativecommons.org/licenses/by/4.0/",
            )
            for index in range(limit)
        ]

    async def get(self, image_id: str):
        self.get_calls.append(image_id)
        if self.fail_get:
            raise RuntimeError("secret provider detail")
        if self.reject_get:
            return None
        return CardImageCandidate(
            image_id=image_id,
            image_url=f"https://images.test/{image_id}.jpg",
            source_url=f"https://source.test/{image_id}",
            creator="Server Creator",
            license="by-sa",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
        )

    async def search_strict(self, query: str, offset: int = 0, limit: int = 3):
        if self.session is not None:
            assert not self.session.in_transaction(), "teacher search must not hold a DB transaction"
        if self.during_search:
            self.during_search()
        if self.fail_search:
            return OpenverseOperationResult(status=OpenverseOperationStatus.UNAVAILABLE)
        if self.search_pages is not None:
            self.search_calls.append((query, offset, limit))
            options = self.search_pages.get(offset, [])
        else:
            options = await self.search(query, offset, limit)
        return OpenverseOperationResult(status=OpenverseOperationStatus.OK, value=options)

    async def get_strict(self, image_id: str):
        if self.session is not None:
            assert not self.session.in_transaction(), "teacher selection must not hold a DB transaction"
        if self.during_get:
            self.during_get()
        if self.fail_get:
            return OpenverseOperationResult(status=OpenverseOperationStatus.UNAVAILABLE)
        candidate = await self.get(image_id)
        result_status = OpenverseOperationStatus.OK if candidate is not None else OpenverseOperationStatus.NOT_FOUND
        return OpenverseOperationResult(status=result_status, value=candidate)


def image_api_client(session: Session, fake: FakeManageImageClient) -> TestClient:
    client = make_client(session)
    client.app.dependency_overrides[get_openverse_image_client] = lambda: fake
    return client


def test_teacher_image_options_return_three_candidates_and_clamped_next_offset():
    session = make_session()
    _, _, draft_card, _ = seed_teacher_profile_and_cards(session)
    draft_card.image_search_query = "saved query"
    session.commit()
    fake = FakeManageImageClient()
    client = image_api_client(session, fake)
    headers = {"x-telegram-init-data": signed_init_data(1001)}

    response = client.get(f"/api/teacher/cards/{draft_card.id}/image-options?offset=7", headers=headers)
    low = client.get(f"/api/teacher/cards/{draft_card.id}/image-options?offset=-8", headers=headers)
    high = client.get(f"/api/teacher/cards/{draft_card.id}/image-options?offset=999", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["options"]) == 3
    assert response.json()["next_offset"] == 10
    assert low.json()["next_offset"] == 3
    assert high.json()["next_offset"] == 303
    assert fake.search_calls == [("saved query", 7, 3), ("saved query", 0, 3), ("saved query", 300, 3)]


def test_teacher_image_options_build_query_when_card_has_none():
    session = make_session()
    _, _, draft_card, _ = seed_teacher_profile_and_cards(session)
    fake = FakeManageImageClient()
    client = image_api_client(session, fake)

    response = client.get(
        f"/api/teacher/cards/{draft_card.id}/image-options",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )

    assert response.status_code == 200
    assert fake.search_calls == [("journey", 0, 3)]


def test_teacher_selects_image_by_id_and_server_refetches_all_metadata():
    session = make_session()
    _, _, draft_card, _ = seed_teacher_profile_and_cards(session)
    fake = FakeManageImageClient()
    client = image_api_client(session, fake)

    response = client.put(
        f"/api/teacher/cards/{draft_card.id}/image",
        headers={"x-telegram-init-data": signed_init_data(1001)},
        json={"image_id": "chosen"},
    )

    assert response.status_code == 200
    assert fake.get_calls == ["chosen"]
    assert response.json()["image_url"] == "https://images.test/chosen.jpg"
    assert response.json()["image_creator"] == "Server Creator"
    stored = session.get(VocabularyCard, draft_card.id)
    assert stored.image_license == "by-sa"
    assert stored.image_search_query == "journey"


def test_teacher_image_selection_rejects_missing_arbitrary_or_provider_rejected_id():
    session = make_session()
    _, _, draft_card, _ = seed_teacher_profile_and_cards(session)
    fake = FakeManageImageClient(reject_get=True)
    client = image_api_client(session, fake)
    headers = {"x-telegram-init-data": signed_init_data(1001)}
    path = f"/api/teacher/cards/{draft_card.id}/image"

    missing = client.put(path, headers=headers, json={})
    arbitrary = client.put(path, headers=headers, json={"image_url": "https://evil.test/image.jpg"})
    extra_metadata = client.put(
        path,
        headers=headers,
        json={"image_id": "chosen", "image_url": "https://evil.test/image.jpg"},
    )
    rejected = client.put(path, headers=headers, json={"image_id": "rejected"})

    assert missing.status_code == 422
    assert arbitrary.status_code == 422
    assert extra_metadata.status_code == 422
    assert rejected.status_code == 422
    assert session.get(VocabularyCard, draft_card.id).image_url is None


def test_teacher_image_selection_hides_provider_failure_detail():
    session = make_session()
    _, _, draft_card, _ = seed_teacher_profile_and_cards(session)
    client = image_api_client(session, FakeManageImageClient(fail_get=True))

    response = client.put(
        f"/api/teacher/cards/{draft_card.id}/image",
        headers={"x-telegram-init-data": signed_init_data(1001)},
        json={"image_id": "chosen"},
    )

    assert response.status_code == 502
    assert "secret provider detail" not in response.text


def test_teacher_image_options_provider_failure_is_502_but_genuine_empty_is_422():
    session = make_session()
    _, _, draft_card, _ = seed_teacher_profile_and_cards(session)
    headers = {"x-telegram-init-data": signed_init_data(1001)}
    path = f"/api/teacher/cards/{draft_card.id}/image-options"

    unavailable = image_api_client(session, FakeManageImageClient(fail_search=True)).get(path, headers=headers)
    empty = image_api_client(session, FakeManageImageClient(search_pages={0: []})).get(path, headers=headers)

    assert unavailable.status_code == 502
    assert empty.status_code == 422


def test_teacher_image_operations_end_read_transaction_and_revalidate_draft_after_provider_await():
    session = make_session()
    _, _, draft_card, _ = seed_teacher_profile_and_cards(session)
    card_id = draft_card.id
    headers = {"x-telegram-init-data": signed_init_data(1001)}

    def publish_during_provider_call():
        card = session.get(VocabularyCard, card_id)
        card.status = "published"
        session.commit()

    options_fake = FakeManageImageClient(session=session, during_search=publish_during_provider_call)
    options = image_api_client(session, options_fake).get(
        f"/api/teacher/cards/{card_id}/image-options", headers=headers
    )
    assert options.status_code == 409

    session.get(VocabularyCard, card_id).status = "draft"
    session.commit()
    selection_fake = FakeManageImageClient(session=session, during_get=publish_during_provider_call)
    selection = image_api_client(session, selection_fake).put(
        f"/api/teacher/cards/{card_id}/image", headers=headers, json={"image_id": "chosen"}
    )

    assert selection.status_code == 409
    assert session.get(VocabularyCard, card_id).image_url is None


def test_teacher_image_options_exclude_current_and_fill_three_unique_from_following_pages():
    session = make_session()
    _, _, draft_card, _ = seed_teacher_profile_and_cards(session)
    draft_card.image_url = "https://images.test/current.jpg"
    draft_card.image_source_url = "https://source.test/current"
    session.commit()

    def candidate(image_id: str, image_url: str, source_url: str) -> CardImageCandidate:
        return CardImageCandidate(
            image_id=image_id,
            image_url=image_url,
            source_url=source_url,
            creator=None,
            license="by",
            license_url=None,
        )

    pages = {
        0: [
            candidate("current", "https://images.test/current.jpg", "https://source.test/other"),
            candidate("one", "https://images.test/one.jpg", "https://source.test/one"),
            candidate("one-copy", "https://images.test/one.jpg", "https://source.test/one-copy"),
        ],
        3: [
            candidate("source-current", "https://images.test/other.jpg", "https://source.test/current"),
            candidate("two", "https://images.test/two.jpg", "https://source.test/two"),
            candidate("three", "https://images.test/three.jpg", "https://source.test/three"),
        ],
    }
    fake = FakeManageImageClient(search_pages=pages)
    response = image_api_client(session, fake).get(
        f"/api/teacher/cards/{draft_card.id}/image-options",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )

    assert response.status_code == 200
    assert [item["image_id"] for item in response.json()["options"]] == ["one", "two", "three"]
    assert response.json()["next_offset"] == 6
    assert fake.search_calls == [("journey", 0, 3), ("journey", 3, 3)]


def test_teacher_removes_image_but_retains_search_query():
    session = make_session()
    _, _, draft_card, _ = seed_teacher_profile_and_cards(session)
    draft_card.image_url = "https://images.test/old.jpg"
    draft_card.image_source_url = "https://source.test/old"
    draft_card.image_creator = "Old Creator"
    draft_card.image_license = "by"
    draft_card.image_license_url = "https://creativecommons.org/licenses/by/4.0/"
    draft_card.image_search_query = "retained query"
    session.commit()
    client = image_api_client(session, FakeManageImageClient())

    response = client.delete(
        f"/api/teacher/cards/{draft_card.id}/image",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )

    assert response.status_code == 200
    for field in ("image_url", "image_source_url", "image_creator", "image_license", "image_license_url"):
        assert response.json()[field] is None
    assert response.json()["image_search_query"] == "retained query"


def test_teacher_image_endpoints_hide_other_teacher_card_and_reject_published_card():
    session = make_session()
    _, _, draft_card, published_card = seed_teacher_profile_and_cards(session)
    fake = FakeManageImageClient()
    client = image_api_client(session, fake)
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="test",
        telegram_bot_token="test-bot-token",
        allowed_telegram_teacher_ids="1001,2002",
        openverse_images_enabled=False,
    )
    session.add(User(telegram_user_id=2002, role="teacher", is_active=True))
    session.commit()
    other_headers = {"x-telegram-init-data": signed_init_data(2002)}
    owner_headers = {"x-telegram-init-data": signed_init_data(1001)}

    other_responses = [
        client.get(f"/api/teacher/cards/{draft_card.id}/image-options", headers=other_headers),
        client.put(
            f"/api/teacher/cards/{draft_card.id}/image",
            headers=other_headers,
            json={"image_id": "chosen"},
        ),
        client.delete(f"/api/teacher/cards/{draft_card.id}/image", headers=other_headers),
    ]
    published_responses = [
        client.get(f"/api/teacher/cards/{published_card.id}/image-options", headers=owner_headers),
        client.put(
            f"/api/teacher/cards/{published_card.id}/image",
            headers=owner_headers,
            json={"image_id": "chosen"},
        ),
        client.delete(f"/api/teacher/cards/{published_card.id}/image", headers=owner_headers),
    ]

    assert [response.status_code for response in other_responses] == [404, 404, 404]
    assert [response.status_code for response in published_responses] == [409, 409, 409]
    assert fake.search_calls == []
    assert fake.get_calls == []


def test_manual_create_commits_draft_then_enriches_with_overridden_client():
    session = make_session()
    _, profile, _, _ = seed_teacher_profile_and_cards(session)
    client = make_client(session)
    fake = FakeCreateImageClient(session=session)
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
    assert fake.queries == ["fluency"]
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


def test_manual_create_survives_optional_image_commit_failure_and_rolls_back(monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    session = make_session()
    _, profile, _, _ = seed_teacher_profile_and_cards(session)
    client = make_client(session)
    fake = FakeCreateImageClient(session=session)
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="test",
        telegram_bot_token="test-bot-token",
        allowed_telegram_teacher_ids="1001",
        openverse_images_enabled=True,
    )
    client.app.dependency_overrides[get_openverse_image_client] = lambda: fake
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
    response = client.post(
        "/api/teacher/cards",
        headers={"x-telegram-init-data": signed_init_data(1001)},
        json={"learning_profile_id": profile.id, "term": "fluency", "translation_ru": "беглость"},
    )

    assert response.status_code == 200
    assert rollback_calls == 1
    stored = session.get(VocabularyCard, response.json()["id"])
    assert stored.status == "draft"
    assert stored.image_url is None
    assert session.query(VocabularyCard).count() == 3
