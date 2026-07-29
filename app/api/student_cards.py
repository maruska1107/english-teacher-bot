from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models import Student, VocabularyCard
from app.repositories.student_card_progress import StudentCardProgressRepository
from app.repositories.students import StudentRepository
from app.repositories.vocabulary_cards import VocabularyCardRepository
from app.schemas.student_cards import (
    StudentCardListResponse,
    StudentCardProgressResponse,
    StudentCardProgressUpdate,
    StudentCardRead,
)
from app.telegram.webapp_auth import TelegramWebAppAuthError, verify_telegram_webapp_init_data

router = APIRouter(prefix="/api/student/cards", tags=["student-cards"])


def get_current_student(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_telegram_init_data: Annotated[str | None, Header()] = None,
) -> Student:
    if not x_telegram_init_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram WebApp initData is required")
    try:
        init_data = verify_telegram_webapp_init_data(x_telegram_init_data, settings)
    except TelegramWebAppAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    student = StudentRepository(session).get_by_telegram_user_id(init_data.user.id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student is not linked")
    return student


def card_to_response(card: VocabularyCard, progress_status: str) -> StudentCardRead:
    return StudentCardRead(
        id=card.id,
        term=card.term,
        translation_ru=card.translation_ru,
        example_sentence=card.example_sentence,
        status=progress_status,
    )


@router.get("", response_model=StudentCardListResponse)
def list_student_cards(
    session: Annotated[Session, Depends(get_db_session)],
    student: Annotated[Student, Depends(get_current_student)],
) -> StudentCardListResponse:
    cards = VocabularyCardRepository(session).list_published_for_student(student.id)
    return StudentCardListResponse(cards=[card_to_response(card, progress_status) for card, progress_status in cards])


@router.post("/{card_id}/progress", response_model=StudentCardProgressResponse)
def update_student_card_progress(
    card_id: int,
    payload: StudentCardProgressUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    student: Annotated[Student, Depends(get_current_student)],
) -> StudentCardProgressResponse:
    card = VocabularyCardRepository(session).get_published_for_student(student.id, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    progress = StudentCardProgressRepository(session).set_status(
        student_id=student.id,
        card_id=card.id,
        status=payload.status,
    )
    session.commit()
    return StudentCardProgressResponse(card_id=card.id, status=progress.status, review_count=progress.review_count)
