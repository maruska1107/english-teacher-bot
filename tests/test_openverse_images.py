import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.models import VocabularyCard
from app.schemas.cards import CardImageCandidate, CardImageSelection
from app.services.openverse_images import (
    OpenverseImageClient,
    OpenverseOperationStatus,
    build_image_query,
    enrich_card_image,
    get_openverse_image_client,
)

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


def test_build_image_query_sends_only_normalized_term_without_personal_context():
    card = make_card(
        term="  make   a journey  ",
        definition_en="Alice Johnson discussed this with Bob Smith",
        source_phrase="Alice Johnson said make a journey",
        example_sentence="Bob Smith made a journey yesterday",
        translation_ru="путешествие Ивана Иванова",
    )

    query = build_image_query(card)

    assert query == "make a journey"
    for private_value in ("Alice", "Johnson", "Bob", "Smith", "Ивана", "Иванова", "17", "23"):
        assert private_value not in query


def test_build_image_query_caps_query_at_documented_300_characters():
    query = build_image_query(make_card(term="word " + "x" * 400))

    assert len(query) == 300
    assert query.startswith("word ")


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("openverse_api_base_url", "http://openverse.test/v1"),
        ("openverse_api_base_url", "/v1"),
        ("openverse_api_base_url", "https:///v1"),
        ("openverse_api_base_url", "https://openverse.test/" + "x" * 2048),
        ("openverse_timeout_seconds", 0),
        ("openverse_timeout_seconds", -1),
        ("openverse_timeout_seconds", 31),
        ("openverse_timeout_seconds", float("nan")),
        ("openverse_timeout_seconds", float("inf")),
        ("openverse_result_page_size", 0),
        ("openverse_result_page_size", 51),
        ("openverse_batch_concurrency", 0),
        ("openverse_batch_concurrency", 11),
        ("openverse_user_agent", "   "),
        ("openverse_user_agent", "x" * 256),
    ],
)
def test_settings_reject_invalid_openverse_values(field_name, invalid_value):
    with pytest.raises(ValidationError):
        make_openverse_settings(**{field_name: invalid_value})


def test_settings_normalize_valid_openverse_strings_and_keep_url_plain_str():
    settings = make_openverse_settings(
        openverse_api_base_url="  https://openverse.test/v1/  ",
        openverse_user_agent="  English Tutor Test/1.0  ",
        openverse_timeout_seconds=30,
        openverse_result_page_size=50,
        openverse_batch_concurrency=10,
    )

    assert settings.openverse_api_base_url == "https://openverse.test/v1"
    assert isinstance(settings.openverse_api_base_url, str)
    assert settings.openverse_user_agent == "English Tutor Test/1.0"


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


async def test_search_processes_at_most_effective_limit_from_oversized_response():
    payload = {
        "results": [
            {
                "id": f"image-{index}",
                "thumbnail": f"https://images.test/{index}.jpg",
                "foreign_landing_url": f"https://source.test/{index}",
                "license": "by",
            }
            for index in range(1000)
        ]
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    async with httpx.AsyncClient(transport=transport) as raw:
        candidates = await OpenverseImageClient(
            make_openverse_settings(openverse_result_page_size=3), async_client=raw
        ).search("fox", limit=50)

    assert [candidate.image_id for candidate in candidates] == ["image-0", "image-1", "image-2"]


async def test_owned_client_is_closed_by_context_manager():
    client = OpenverseImageClient(make_openverse_settings())
    owned_http_client = client._async_client

    async with client:
        assert not owned_http_client.is_closed

    assert owned_http_client.is_closed


async def test_injected_client_remains_caller_owned_after_wrapper_close():
    injected = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
    client = OpenverseImageClient(make_openverse_settings(), async_client=injected)

    await client.aclose()

    assert not injected.is_closed
    await injected.aclose()


async def test_fastapi_dependency_closes_its_owned_client():
    dependency = get_openverse_image_client(make_openverse_settings())
    client = await anext(dependency)
    owned_http_client = client._async_client

    await dependency.aclose()

    assert owned_http_client.is_closed


@pytest.mark.parametrize("status_code", [429, 500])
async def test_search_returns_empty_for_http_errors(status_code):
    transport = httpx.MockTransport(lambda request: httpx.Response(status_code, json={"detail": "do not log me"}))
    async with httpx.AsyncClient(transport=transport) as async_client:
        result = await OpenverseImageClient(make_openverse_settings(), async_client=async_client).search("fox")
    assert result == []


@pytest.mark.parametrize("status_code", [429, 500, 503])
async def test_strict_search_reports_http_provider_outages(status_code):
    transport = httpx.MockTransport(lambda request: httpx.Response(status_code, json={"detail": "private"}))
    async with httpx.AsyncClient(transport=transport) as async_client:
        result = await OpenverseImageClient(make_openverse_settings(), async_client=async_client).search_strict("fox")

    assert result.status is OpenverseOperationStatus.UNAVAILABLE
    assert result.value is None


async def test_strict_search_reports_timeout_without_mutable_client_error_state():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("private timeout detail", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as async_client:
        client = OpenverseImageClient(make_openverse_settings(), async_client=async_client)
        result = await client.search_strict("fox")

    assert result.status is OpenverseOperationStatus.UNAVAILABLE
    assert result.value is None
    assert not hasattr(client, "last_error")


async def test_strict_search_distinguishes_genuine_empty_results():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"results": []}))
    async with httpx.AsyncClient(transport=transport) as async_client:
        result = await OpenverseImageClient(make_openverse_settings(), async_client=async_client).search_strict("fox")

    assert result.status is OpenverseOperationStatus.OK
    assert result.value == []


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


@pytest.mark.parametrize("error_type", [httpx.RemoteProtocolError, httpx.ProxyError])
@pytest.mark.parametrize(("method_name", "argument", "expected"), [("search", "fox", []), ("get", "image-id", None)])
async def test_requests_safely_fall_back_for_other_httpx_errors(error_type, method_name, argument, expected, caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        raise error_type("sensitive upstream details", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as async_client:
        client = OpenverseImageClient(make_openverse_settings(), async_client=async_client)
        result = await getattr(client, method_name)(argument)

    assert result == expected
    assert [record.getMessage() for record in caplog.records] == [f"Openverse request failed: {error_type.__name__}"]


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


@pytest.mark.parametrize("status_code", [429, 500, 503])
async def test_strict_get_reports_http_provider_outages(status_code):
    transport = httpx.MockTransport(lambda request: httpx.Response(status_code))
    async with httpx.AsyncClient(transport=transport) as async_client:
        result = await OpenverseImageClient(make_openverse_settings(), async_client=async_client).get_strict("image-id")

    assert result.status is OpenverseOperationStatus.UNAVAILABLE
    assert result.value is None


async def test_strict_get_distinguishes_provider_not_found():
    transport = httpx.MockTransport(lambda request: httpx.Response(404, json={"detail": "not found"}))
    async with httpx.AsyncClient(transport=transport) as async_client:
        result = await OpenverseImageClient(make_openverse_settings(), async_client=async_client).get_strict("missing")

    assert result.status is OpenverseOperationStatus.NOT_FOUND
    assert result.value is None


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
        assert card.image_search_query == "make a journey"


async def test_enrichment_sets_valid_image_metadata_from_first_result():
    session = make_session()
    card = make_card()
    session.add(card)
    candidate = CardImageCandidate(**VALID_CANDIDATE)
    fake = FakeImageClient([candidate])

    changed = await enrich_card_image(session, card, make_openverse_settings(), fake)

    assert changed is True
    assert fake.queries == [("make a journey", 0, 1)]
    assert card.image_url == candidate.image_url
    assert card.image_source_url == candidate.source_url
    assert card.image_search_query == fake.queries[0][0]
