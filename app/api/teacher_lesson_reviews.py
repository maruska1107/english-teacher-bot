from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.teacher_cards import get_current_teacher, get_teacher_profile_or_404
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models import LearningProfileMember, Lesson, LessonAnalysis, Student, StudentHomework, User, VocabularyCard
from app.repositories.student_homework import StudentHomeworkRepository
from app.repositories.vocabulary_cards import VocabularyCardRepository
from app.schemas.cards import VocabularyCardRead, VocabularyCardUpdate
from app.schemas.student_cards import StudentHomeworkListResponse, StudentHomeworkRead
from app.schemas.teacher_lesson_reviews import (
    TeacherLessonReviewConfirmResponse,
    TeacherLessonReviewListResponse,
    TeacherLessonReviewRead,
)
from app.telegram.messages import STUDENT_HOMEWORK_READY_TEXT_TEMPLATE
from app.telegram.notifier import TelegramBotNotifier, TelegramNotifierProtocol

router = APIRouter(prefix="/api/teacher/lesson-reviews", tags=["teacher-lesson-reviews"])
homework_router = APIRouter(prefix="/api/teacher/homework", tags=["teacher-homework"])


def get_telegram_notifier(settings: Annotated[Settings, Depends(get_settings)]) -> TelegramNotifierProtocol:
    return TelegramBotNotifier(settings)


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


def _draft_cards_for_lesson(session: Session, lesson_id: int) -> list[VocabularyCard]:
    return list(
        session.scalars(
            select(VocabularyCard)
            .where(VocabularyCard.lesson_id == lesson_id, VocabularyCard.status == "draft")
            .order_by(VocabularyCard.created_at.desc(), VocabularyCard.id.desc())
        )
    )


def _card_to_response(card: VocabularyCard) -> VocabularyCardRead:
    return VocabularyCardRead(
        id=card.id,
        learning_profile_id=card.learning_profile_id,
        term=card.term,
        translation_ru=card.translation_ru,
        definition_en=card.definition_en,
        example_sentence=card.example_sentence,
        source_phrase=card.source_phrase,
        level=card.level,
        status=card.status,
        image_url=card.image_url,
        image_source_url=card.image_source_url,
        image_creator=card.image_creator,
        image_license=card.image_license,
        image_license_url=card.image_license_url,
        image_search_query=card.image_search_query,
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


def _students_for_profile(session: Session, profile_id: int) -> list[Student]:
    return list(
        session.scalars(
            select(Student)
            .join(LearningProfileMember, LearningProfileMember.student_id == Student.id)
            .where(LearningProfileMember.learning_profile_id == profile_id)
            .order_by(Student.id)
        )
    )


async def _notify_students_homework_ready(
    notifier: TelegramNotifierProtocol,
    students: list[Student],
    published_count: int,
) -> None:
    text = STUDENT_HOMEWORK_READY_TEXT_TEMPLATE.format(card_count=published_count)
    for student in students:
        if student.telegram_user_id is None:
            continue
        await notifier.send_webapp_button(
            student.telegram_user_id,
            text,
            "Открыть ДЗ и карточки",
            "https://englishtutorai.ru/student/cards",
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
        profile_id=lesson.learning_profile_id,
        student_name=student.name,
        lesson_date_label="После урока",
        summary_text=_summary_text(analysis),
        homework_items=_homework_items(analysis),
        new_cards_count=_draft_card_count(session, lesson.id),
        cards=[_card_to_response(card) for card in _draft_cards_for_lesson(session, lesson.id)],
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
async def confirm_lesson_review(
    lesson_id: int,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
    notifier: Annotated[TelegramNotifierProtocol, Depends(get_telegram_notifier)],
) -> TeacherLessonReviewConfirmResponse:
    lesson = session.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.teacher_user_id == teacher.id))
    if lesson is None or lesson.analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson review not found")
    if lesson.learning_profile_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    students = _students_for_profile(session, lesson.learning_profile_id)
    if not students:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if _is_published(session, lesson.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lesson review already sent")

    analysis = lesson.analysis
    published_count = VocabularyCardRepository(session).publish_draft_cards_for_lesson(teacher.id, lesson.id)
    homework_repository = StudentHomeworkRepository(session)
    homework = None
    for student in students:
        homework = homework_repository.publish_current(
            student_id=student.id,
            learning_profile_id=lesson.learning_profile_id,
            lesson_id=lesson.id,
            lesson_date_label="После урока",
            summary_text=_summary_text(analysis),
            wins_text=_wins_text(analysis),
            focus_text=_focus_text(analysis),
            homework_items=_homework_items(analysis),
            new_cards_count=published_count,
        )
    session.commit()
    assert homework is not None
    await _notify_students_homework_ready(notifier, students, published_count)
    return TeacherLessonReviewConfirmResponse(**_homework_to_response(homework).model_dump())


def _get_review_draft_card_or_404(session: Session, teacher: User, card_id: int) -> VocabularyCard:
    card = session.scalar(
        select(VocabularyCard)
        .join(Lesson, Lesson.id == VocabularyCard.lesson_id)
        .where(
            VocabularyCard.id == card_id,
            VocabularyCard.teacher_user_id == teacher.id,
            VocabularyCard.status == "draft",
            Lesson.teacher_user_id == teacher.id,
        )
    )
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review card not found")
    return card


@router.patch("/cards/{card_id}", response_model=VocabularyCardRead)
def update_review_card(
    card_id: int,
    payload: VocabularyCardUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> VocabularyCardRead:
    card = _get_review_draft_card_or_404(session, teacher, card_id)
    updated = VocabularyCardRepository(session).update_card(card, payload)
    session.commit()
    return _card_to_response(updated)


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review_card(
    card_id: int,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> Response:
    card = _get_review_draft_card_or_404(session, teacher, card_id)
    VocabularyCardRepository(session).delete_card(card)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
