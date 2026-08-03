import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.models import VocabularyCard
from app.schemas.cards import CardImageCandidate, CardImageSelection
from app.services.openverse_images import OpenverseImageClient, build_image_query, enrich_card_image

VALID_CANDIDATE = {
    "image_id": "openverse-1",
    "image_url": "https://api.openverse.org/v1/images/openverse-1/thumb/",
    "source_url": "https://example.org/source",
    "creator": "Alice",
    "license": "by",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
}


def test_card_image_candidate_accepts_https_strings_and_normalizes_whitespace():
    candidate = CardImageCandidate(
        image_id="  openverse-1  ",
        image_url="  https://api.openverse.org/v1/images/openverse-1/thumb/  ",
        source_url="  https://example.org/source  ",
        creator="  Alice  ",
        license="by",
        license_url="  https://creativecommons.org/licenses/by/4.0/  ",
    )

    assert candidate.image_id == "openverse-1"
    assert candidate.image_url == "https://api.openverse.org/v1/images/openverse-1/thumb/"
    assert candidate.source_url == "https://example.org/source"
    assert candidate.creator == "Alice"
    assert candidate.license_url == "https://creativecommons.org/licenses/by/4.0/"
    assert isinstance(candidate.image_url, str)
    assert isinstance(candidate.source_url, str)
    assert isinstance(candidate.license_url, str)


@pytest.mark.parametrize("field_name", ["image_url", "source_url", "license_url"])
@pytest.mark.parametrize(
    "invalid_url",
    [
        "http://example.org/image",
        "javascript:alert(1)",
        "data:image/png;base64,AAAA",
        "/relative/image.png",
        "https:///hostless",
        "https://exa mple.org/image",
    ],
)
def test_card_image_candidate_rejects_unsafe_or_non_absolute_urls(field_name, invalid_url):
    payload = {**VALID_CANDIDATE, field_name: invalid_url}

    with pytest.raises(ValidationError):
        CardImageCandidate(**payload)


@pytest.mark.parametrize("field_name", ["image_url", "source_url", "license_url"])
@pytest.mark.parametrize("invalid_url", ["   ", f"https://example.org/{'x' * 2030}"])
def test_card_image_candidate_rejects_empty_or_overlong_urls(field_name, invalid_url):
    payload = {**VALID_CANDIDATE, field_name: invalid_url}

    with pytest.raises(ValidationError):
        CardImageCandidate(**payload)


def test_card_image_candidate_allows_null_license_url():
    candidate = CardImageCandidate(**{**VALID_CANDIDATE, "license_url": None})

    assert candidate.license_url is None


def test_card_image_candidate_enforces_normalized_image_id_length():
    candidate = CardImageCandidate(**{**VALID_CANDIDATE, "image_id": f"  {'x' * 100}  "})

    assert candidate.image_id == "x" * 100
    for invalid_image_id in ("   ", "x" * 101):
        with pytest.raises(ValidationError):
            CardImageCandidate(**{**VALID_CANDIDATE, "image_id": invalid_image_id})


def test_card_image_candidate_enforces_normalized_creator_length():
    candidate = CardImageCandidate(**{**VALID_CANDIDATE, "creator": f"  {'x' * 255}  "})

    assert candidate.creator == "x" * 255
    with pytest.raises(ValidationError):
        CardImageCandidate(**{**VALID_CANDIDATE, "creator": "x" * 256})


def test_card_image_candidate_normalizes_blank_creator_to_none():
    candidate = CardImageCandidate(**{**VALID_CANDIDATE, "creator": "   "})

    assert candidate.creator is None


def test_card_image_selection_strips_valid_id_and_rejects_whitespace_only_id():
    assert CardImageSelection(image_id="  openverse-1  ").image_id == "openverse-1"
    with pytest.raises(ValidationError):
        CardImageSelection(image_id="   ")


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def make_card(**overrides) -> VocabularyCard:
    values = {
        "teacher_user_id": 17,
        "learning_profile_id": 23,
        "term": "  make   a journey ",
        "translation_ru": "совершить путешествие секрет-1001",
        "definition_en": " to travel   somewhere ",
        "source_phrase": "make a journey",
        "example_sentence": " We made a journey yesterday. ",
        "status": "draft",
    }
    values.update(overrides)
    return VocabularyCard(**values)


def make_openverse_settings(**overrides) -> Settings:
    values = {"app_env": "test", "openverse_api_base_url": "https://openverse.test/v1"}
    values.update(overrides)
    return Settings(**values)


def test_build_image_query_uses_only_normalized_english_card_content_and_deduplicates():
    card = make_card(source_phrase="  make   a journey  ", example_sentence="to travel somewhere")

    query = build_image_query(card)

    assert query == "make a journey to travel somewhere"
    assert "совершить" not in query
    assert "1001" not in query
    assert "17" not in query
    assert "23" not in query


def test_build_image_query_caps_query_at_documented_300_characters():
    query = build_image_query(
        make_card(term="word", definition_en="d" * 200, source_phrase="s" * 200, example_sentence="e" * 200)
    )

    assert len(query) == 300
    assert query.startswith("word ")


async def test_search_sends_exact_headers_timeout_params_and_page_mapping():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"results": []})

    settings = make_openverse_settings(openverse_result_page_size=3, openverse_timeout_seconds=4.0)
    async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OpenverseImageClient(settings, async_client=async_client)

    assert await client.search("red fox", offset=6, limit=99) == []
    await async_client.aclose()

    request = requests[0]
    assert request.headers["user-agent"] == "EnglishTutorAI/0.1 (support@englishtutorai.ru)"
    assert request.url.path == "/v1/images/"
    assert dict(request.url.params) == {
        "q": "red fox",
        "page_size": "3",
        "page": "3",
        "license_type": "commercial",
        "license": "cc0,pdm,by,by-sa",
    }
    assert request.extensions["timeout"] == {"connect": 4.0, "read": 4.0, "write": 4.0, "pool": 4.0}


async def test_search_parses_valid_candidates_and_filters_each_malformed_result():
    payload = {
        "results": [
            {
                "id": "valid-thumb",
                "thumbnail": "https://images.test/thumb.jpg",
                "url": "https://images.test/original.jpg",
                "foreign_landing_url": "https://source.test/item",
                "creator": "Alice",
                "license": "by",
                "license_url": "https://creativecommons.org/licenses/by/4.0/",
            },
            {
                "id": "valid-url",
                "thumbnail": None,
                "url": "https://images.test/original-2.jpg",
                "foreign_landing_url": "https://source.test/item-2",
                "creator": None,
                "license": "cc0",
                "license_url": None,
            },
            {
                "id": "http",
                "thumbnail": "http://unsafe.test/x",
                "foreign_landing_url": "https://source.test",
                "license": "by",
            },
            {
                "id": "bad-license",
                "thumbnail": "https://images.test/x",
                "foreign_landing_url": "https://source.test",
                "license": "nc",
            },
            {"id": "missing-fields"},
            "not-an-object",
        ]
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    async with httpx.AsyncClient(transport=transport) as async_client:
        candidates = await OpenverseImageClient(make_openverse_settings(), async_client=async_client).search("fox")

    assert [candidate.image_id for candidate in candidates] == ["valid-thumb", "valid-url"]
    assert candidates[0].image_url == "https://images.test/thumb.jpg"
    assert candidates[1].image_url == "https://images.test/original-2.jpg"
    assert isinstance(candidates[0].image_url, str)
    assert isinstance(candidates[0].source_url, str)
    assert isinstance(candidates[0].license_url, str)


@pytest.mark.parametrize("status_code", [429, 500])
async def test_search_returns_empty_for_http_errors(status_code):
    transport = httpx.MockTransport(lambda request: httpx.Response(status_code, json={"detail": "do not log me"}))
    async with httpx.AsyncClient(transport=transport) as async_client:
        result = await OpenverseImageClient(make_openverse_settings(), async_client=async_client).search("fox")
    assert result == []


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, json={"results": {"wrong": "shape"}}),
        httpx.Response(200, json={}),
        httpx.Response(200, content=b""),
    ],
)
async def test_search_returns_empty_for_malformed_or_empty_payload(response):
    transport = httpx.MockTransport(lambda request: response)
    async with httpx.AsyncClient(transport=transport) as async_client:
        result = await OpenverseImageClient(make_openverse_settings(), async_client=async_client).search("fox")
    assert result == []


@pytest.mark.parametrize("error_type", [httpx.TimeoutException, httpx.ConnectError])
async def test_search_returns_empty_for_timeout_and_connection_errors(error_type):
    def handler(request: httpx.Request) -> httpx.Response:
        raise error_type("network unavailable", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as async_client:
        result = await OpenverseImageClient(make_openverse_settings(), async_client=async_client).search("fox")
    assert result == []


async def test_get_encodes_image_id_as_one_safe_path_segment_and_parses_candidate():
    paths: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.raw_path)
        return httpx.Response(
            200,
            json={
                **VALID_CANDIDATE,
                "id": "folder/image id",
                "thumbnail": VALID_CANDIDATE["image_url"],
                "foreign_landing_url": VALID_CANDIDATE["source_url"],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as async_client:
        client = OpenverseImageClient(make_openverse_settings(), async_client=async_client)
        candidate = await client.get("folder/image id")

    assert paths == [b"/v1/images/folder%2Fimage%20id/"]
    assert candidate is not None
    assert candidate.image_id == "folder/image id"


@pytest.mark.parametrize("image_id", ["", "   ", "x" * 101])
async def test_get_rejects_invalid_image_id_without_request(image_id):
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as async_client:
        result = await OpenverseImageClient(make_openverse_settings(), async_client=async_client).get(image_id)
    assert result is None
    assert request_count == 0


class FakeImageClient:
    def __init__(self, results=None, error: Exception | None = None) -> None:
        self.results = results or []
        self.error = error
        self.queries: list[tuple[str, int, int]] = []

    async def search(self, query: str, offset: int = 0, limit: int = 3):
        self.queries.append((query, offset, limit))
        if self.error:
            raise self.error
        return self.results

    async def get(self, image_id: str):
        raise AssertionError("get should not be called")


async def test_enrichment_disabled_does_not_request_or_change_card():
    session = make_session()
    card = make_card()
    fake = FakeImageClient(error=AssertionError("network must not be called"))

    changed = await enrich_card_image(session, card, make_openverse_settings(openverse_images_enabled=False), fake)

    assert changed is False
    assert fake.queries == []
    assert card.image_search_query is None


async def test_enrichment_stores_query_when_search_is_empty_or_fails():
    for fake in (FakeImageClient(), FakeImageClient(error=httpx.ConnectError("offline"))):
        session = make_session()
        card = make_card()
        session.add(card)

        changed = await enrich_card_image(session, card, make_openverse_settings(), fake)

        assert changed is False
        assert card.image_search_query == "make a journey to travel somewhere We made a journey yesterday."


async def test_enrichment_sets_valid_image_metadata_from_first_result():
    session = make_session()
    card = make_card()
    session.add(card)
    candidate = CardImageCandidate(**VALID_CANDIDATE)
    fake = FakeImageClient([candidate])

    changed = await enrich_card_image(session, card, make_openverse_settings(), fake)

    assert changed is True
    assert fake.queries == [("make a journey to travel somewhere We made a journey yesterday.", 0, 1)]
    assert card.image_url == candidate.image_url
    assert card.image_source_url == candidate.source_url
    assert card.image_search_query == fake.queries[0][0]
