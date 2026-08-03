from typing import Literal

from pydantic import BaseModel, Field


class CardImageCandidate(BaseModel):
    image_id: str
    image_url: str
    source_url: str
    creator: str | None = None
    license: Literal["cc0", "pdm", "by", "by-sa"]
    license_url: str | None = None


class CardImageOptionsResponse(BaseModel):
    options: list[CardImageCandidate]
    next_offset: int


class CardImageSelection(BaseModel):
    image_id: str = Field(min_length=1, max_length=100)


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
