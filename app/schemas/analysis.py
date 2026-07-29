from pydantic import BaseModel, Field


class Mistake(BaseModel):
    quote: str = Field(min_length=1)
    correction: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class VocabularyCardCandidate(BaseModel):
    term: str = Field(min_length=1)
    translation_ru: str = Field(min_length=1)
    definition_en: str | None = None
    example_sentence: str | None = None
    source_phrase: str | None = None
    level: str | None = None


class LessonAnalysisResult(BaseModel):
    summary: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    mistakes: list[Mistake] = Field(default_factory=list)
    vocabulary: list[str] = Field(default_factory=list)
    vocabulary_cards: list[VocabularyCardCandidate] = Field(default_factory=list)
    homework: list[str] = Field(default_factory=list)
    teacher_recommendations: list[str] = Field(default_factory=list)
    student_message: str = Field(min_length=1)
