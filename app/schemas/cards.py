from pydantic import BaseModel, Field


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


class VocabularyCardListResponse(BaseModel):
    cards: list[VocabularyCardRead]


class VocabularyCardUpdate(BaseModel):
    term: str | None = Field(default=None, min_length=1)
    translation_ru: str | None = Field(default=None, min_length=1)
    definition_en: str | None = None
    example_sentence: str | None = None
    source_phrase: str | None = None
    level: str | None = None
