from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.teacher_cards import get_current_teacher, get_teacher_profile_or_404
from app.db.session import get_db_session
from app.models import LearningProfileMember, Lesson, LessonAnalysis, Student, StudentHomework, User, VocabularyCard
from app.repositories.student_homework import StudentHomeworkRepository
from app.schemas.student_cards import StudentHomeworkListResponse, StudentHomeworkRead
from app.schemas.teacher_lesson_reviews import (
    TeacherLessonReviewConfirmResponse,
    TeacherLessonReviewListResponse,
    TeacherLessonReviewRead,
)

router = APIRouter(prefix="/api/teacher/lesson-reviews", tags=["teacher-lesson-reviews"])
homework_router = APIRouter(prefix="/api/teacher/homework", tags=["teacher-homework"])


def _analysis_data(analysis: LessonAnalysis) -> dict[str, Any]:
    return analysis.analysis_json or {}


def _homework_items(analysis: LessonAnalysis) -> list[str]:
    data = _analysis_data(analysis)
    return [str(item).strip() for item in data.get("homework", []) if str(item).strip()]


def _summary_text(analysis: LessonAnalysis) -> str:
    data = _analysis_data(analysis)
    summary = str(data.get("summary") or "").strip()
    return summary or analysis.student_message.strip()


def _wins_text(analysis: LessonAnalysis) -> str:
    strengths = _analysis_data(analysis).get("strengths", [])
    return "\n".join(str(item).strip() for item in strengths if str(item).strip())


def _focus_text(analysis: LessonAnalysis) -> str:
    mistakes = _analysis_data(analysis).get("mistakes", [])
    lines: list[str] = []
    for mistake in mistakes:
        if not isinstance(mistake, dict):
            continue
        quote = str(mistake.get("quote") or "").strip()
        correction = str(mistake.get("correction") or "").strip()
        explanation = str(mistake.get("explanation") or "").strip()
        if quote:
            lines.append(f"❌ {quote}")
        if correction:
            lines.append(f"✅ {correction}")
        if explanation:
            lines.append(explanation)
    return "\n".join(lines)


def _draft_card_count(session: Session, lesson_id: int) -> int:
    return (
        session.scalar(
            select(func.count(VocabularyCard.id)).where(
                VocabularyCard.lesson_id == lesson_id,
                VocabularyCard.status == "draft",
            )
        )
        or 0
    )


def _student_for_lesson(session: Session, lesson: Lesson) -> Student | None:
    if lesson.learning_profile_id is None:
        return None
    return session.scalar(
        select(Student)
        .join(LearningProfileMember, LearningProfileMember.student_id == Student.id)
        .where(LearningProfileMember.learning_profile_id == lesson.learning_profile_id)
        .order_by(Student.id)
        .limit(1)
    )


def _student_for_profile(session: Session, profile_id: int) -> Student | None:
    return session.scalar(
        select(Student)
        .join(LearningProfileMember, LearningProfileMember.student_id == Student.id)
        .where(LearningProfileMember.learning_profile_id == profile_id)
        .order_by(Student.id)
        .limit(1)
    )


def _is_published(session: Session, lesson_id: int) -> bool:
    return session.scalar(select(StudentHomework.id).where(StudentHomework.lesson_id == lesson_id).limit(1)) is not None


def _review_to_response(session: Session, analysis: LessonAnalysis) -> TeacherLessonReviewRead | None:
    lesson = analysis.lesson
    student = _student_for_lesson(session, lesson)
    if student is None:
        return None
    return TeacherLessonReviewRead(
        lesson_id=lesson.id,
        student_name=student.name,
        lesson_date_label="После урока",
        summary_text=_summary_text(analysis),
        homework_items=_homework_items(analysis),
        new_cards_count=_draft_card_count(session, lesson.id),
    )


def _homework_to_response(homework: StudentHomework) -> StudentHomeworkRead:
    return StudentHomeworkRead(
        slot=homework.slot,
        lesson_date_label=homework.lesson_date_label,
        summary_text=homework.summary_text,
        wins_text=homework.wins_text,
        focus_text=homework.focus_text,
        homework_items=homework.homework_items,
        new_cards_count=homework.new_cards_count,
    )


@router.get("", response_model=TeacherLessonReviewListResponse)
def list_lesson_reviews(
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> TeacherLessonReviewListResponse:
    analyses = session.scalars(
        select(LessonAnalysis)
        .join(Lesson)
        .where(Lesson.teacher_user_id == teacher.id)
        .where(Lesson.learning_profile_id.is_not(None))
        .order_by(Lesson.created_at.desc(), Lesson.id.desc())
    ).all()
    reviews = []
    for analysis in analyses:
        if _is_published(session, analysis.lesson_id):
            continue
        review = _review_to_response(session, analysis)
        if review is not None:
            reviews.append(review)
    return TeacherLessonReviewListResponse(reviews=reviews)


@router.post("/{lesson_id}/confirm", response_model=TeacherLessonReviewConfirmResponse)
def confirm_lesson_review(
    lesson_id: int,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> TeacherLessonReviewConfirmResponse:
    lesson = session.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.teacher_user_id == teacher.id))
    if lesson is None or lesson.analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson review not found")
    student = _student_for_lesson(session, lesson)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if _is_published(session, lesson.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lesson review already sent")

    analysis = lesson.analysis
    homework = StudentHomeworkRepository(session).publish_current(
        student_id=student.id,
        learning_profile_id=lesson.learning_profile_id,
        lesson_id=lesson.id,
        lesson_date_label="После урока",
        summary_text=_summary_text(analysis),
        wins_text=_wins_text(analysis),
        focus_text=_focus_text(analysis),
        homework_items=_homework_items(analysis),
        new_cards_count=_draft_card_count(session, lesson.id),
    )
    session.commit()
    return TeacherLessonReviewConfirmResponse(**_homework_to_response(homework).model_dump())


@homework_router.get("", response_model=StudentHomeworkListResponse)
def list_teacher_homework(
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
    profile_id: Annotated[int, Query()],
) -> StudentHomeworkListResponse:
    profile = get_teacher_profile_or_404(session, teacher, profile_id)
    student = _student_for_profile(session, profile.id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    items = StudentHomeworkRepository(session).current_and_previous(student.id)
    return StudentHomeworkListResponse(items=[_homework_to_response(item) for item in items])
