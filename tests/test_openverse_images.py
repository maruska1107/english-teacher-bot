import pytest
from pydantic import ValidationError

from app.schemas.cards import CardImageCandidate, CardImageSelection

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
