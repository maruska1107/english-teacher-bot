from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AnyUrl, BaseModel, Field, StringConstraints, TypeAdapter, ValidationError, field_validator

ImageId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
HttpsUrl = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2048)]
Creator = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
_url_adapter = TypeAdapter(AnyUrl)


class CardImageCandidate(BaseModel):
    image_id: ImageId
    image_url: HttpsUrl
    source_url: HttpsUrl
    creator: Creator | None = None
    license: Literal["cc0", "pdm", "by", "by-sa"]
    license_url: HttpsUrl | None = None

    @field_validator("image_url", "source_url", "license_url")
    @classmethod
    def validate_https_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parsed_url = _url_adapter.validate_python(value)
        except ValidationError as exc:
            raise ValueError("must be a valid absolute HTTPS URL") from exc
        if parsed_url.scheme != "https" or not parsed_url.host or not urlsplit(value).netloc:
            raise ValueError("must be a valid absolute HTTPS URL")
        return value

    @field_validator("creator", mode="before")
    @classmethod
    def normalize_creator(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value


class CardImageOptionsResponse(BaseModel):
    options: list[CardImageCandidate]
    next_offset: int


class CardImageSelection(BaseModel):
    image_id: ImageId


class VocabularyCardRead(BaseModel):
    id: int
    learning_profile_id: int
    term: str
    translation_ru: str
    definition_en: str | None = None
    example_sentence: str | None = None
    source_phrase: str | None = None
    level: str | None = None
    status: str
    image_url: str | None = None
    image_source_url: str | None = None
    image_creator: str | None = None
    image_license: str | None = None
    image_license_url: str | None = None
    image_search_query: str | None = None


class VocabularyCardListResponse(BaseModel):
    cards: list[VocabularyCardRead]


class TeacherCardProfileRead(BaseModel):
    id: int
    name: str
    profile_type: str
    new_card_count: int
    published_card_count: int


class TeacherCardProfileListResponse(BaseModel):
    profiles: list[TeacherCardProfileRead]


class TeacherProfileCreateRequest(BaseModel):
    profile_type: Literal["individual", "group"]
    name: str = Field(min_length=1, max_length=120)
    member_names: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name is required")
        return normalized

    @field_validator("member_names")
    @classmethod
    def normalize_members(cls, value: list[str]) -> list[str]:
        member_names = []
        seen_names = set()
        for raw_name in value:
            name = raw_name.strip()
            if name and name not in seen_names:
                member_names.append(name)
                seen_names.add(name)
        return member_names


class TeacherProfileStudentInviteRead(BaseModel):
    name: str
    invite_link: str


class TeacherProfileCreateResponse(BaseModel):
    profile: TeacherCardProfileRead
    students: list[TeacherProfileStudentInviteRead]


class VocabularyCardCreate(BaseModel):
    learning_profile_id: int
    term: str = Field(min_length=1)
    translation_ru: str = Field(min_length=1)
    definition_en: str | None = None
    example_sentence: str | None = None
    source_phrase: str | None = None
    level: str | None = None


class BatchPublishCardsRequest(BaseModel):
    learning_profile_id: int


class BatchPublishCardsResponse(BaseModel):
    published_count: int


class VocabularyCardUpdate(BaseModel):
    term: str | None = Field(default=None, min_length=1)
    translation_ru: str | None = Field(default=None, min_length=1)
    definition_en: str | None = None
    example_sentence: str | None = None
    source_phrase: str | None = None
    level: str | None = None
