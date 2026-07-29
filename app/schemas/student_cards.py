from pydantic import BaseModel, Field


class StudentCardRead(BaseModel):
    id: int
    term: str
    translation_ru: str
    example_sentence: str | None = None
    status: str


class StudentCardListResponse(BaseModel):
    cards: list[StudentCardRead]


class StudentCardProgressUpdate(BaseModel):
    status: str = Field(pattern="^(new|learning|known)$")


class StudentCardProgressResponse(BaseModel):
    card_id: int
    status: str
    review_count: int
