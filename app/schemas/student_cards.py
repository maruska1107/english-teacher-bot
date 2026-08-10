from pydantic import BaseModel, Field


class StudentCardRead(BaseModel):
    id: int
    term: str
    translation_ru: str
    example_sentence: str | None = None
    status: str
    image_url: str | None = None
    image_source_url: str | None = None
    image_creator: str | None = None
    image_license: str | None = None
    image_license_url: str | None = None
    image_search_query: str | None = None


class StudentCardListResponse(BaseModel):
    cards: list[StudentCardRead]


class StudentCardProgressUpdate(BaseModel):
    status: str = Field(pattern="^(new|learning|known)$")


class StudentCardProgressResponse(BaseModel):
    card_id: int
    status: str
    review_count: int


class StudentHomeworkRead(BaseModel):
    slot: str
    lesson_date_label: str
    summary_text: str
    wins_text: str
    focus_text: str
    homework_items: list[str]
    new_cards_count: int


class StudentHomeworkListResponse(BaseModel):
    items: list[StudentHomeworkRead]
