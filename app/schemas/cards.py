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
