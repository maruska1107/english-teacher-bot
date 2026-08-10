from pydantic import BaseModel

from app.schemas.student_cards import StudentHomeworkRead


class TeacherLessonReviewRead(BaseModel):
    lesson_id: int
    student_name: str
    lesson_date_label: str
    summary_text: str
    homework_items: list[str]
    new_cards_count: int


class TeacherLessonReviewListResponse(BaseModel):
    reviews: list[TeacherLessonReviewRead]


class TeacherLessonReviewConfirmResponse(StudentHomeworkRead):
    pass
