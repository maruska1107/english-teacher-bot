from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models import LearningProfile, User, VocabularyCard
from app.repositories.learning_profiles import LearningProfileRepository
from app.repositories.users import UserRepository
from app.repositories.vocabulary_cards import VocabularyCardRepository
from app.schemas.cards import (
    BatchPublishCardsRequest,
    BatchPublishCardsResponse,
    TeacherCardProfileListResponse,
    TeacherCardProfileRead,
    VocabularyCardCreate,
    VocabularyCardListResponse,
    VocabularyCardRead,
    VocabularyCardUpdate,
)
from app.telegram.webapp_auth import TelegramWebAppAuthError, verify_telegram_webapp_init_data

router = APIRouter(prefix="/api/teacher/cards", tags=["teacher-cards"])
profiles_router = APIRouter(prefix="/api/teacher/card-profiles", tags=["teacher-card-profiles"])


def card_to_response(card: VocabularyCard) -> VocabularyCardRead:
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
    )


def get_current_teacher(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_telegram_init_data: Annotated[str | None, Header()] = None,
) -> User:
    if not x_telegram_init_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram WebApp initData is required")
    try:
        init_data = verify_telegram_webapp_init_data(x_telegram_init_data, settings)
    except TelegramWebAppAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    telegram_user_id = init_data.user.id
    if telegram_user_id not in settings.allowed_teacher_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher is not allowed")
    teacher = UserRepository(session).get_by_telegram_id(telegram_user_id)
    if teacher is None:
        teacher = UserRepository(session).get_or_create_teacher(telegram_user_id)
        session.commit()
    return teacher


def profile_to_response(profile: LearningProfile, new_count: int, published_count: int) -> TeacherCardProfileRead:
    return TeacherCardProfileRead(
        id=profile.id,
        name=profile.name,
        profile_type=profile.profile_type,
        new_card_count=new_count,
        published_card_count=published_count,
    )


def get_teacher_profile_or_404(session: Session, teacher: User, profile_id: int) -> LearningProfile:
    profile = session.get(LearningProfile, profile_id)
    if profile is None or profile.teacher_user_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@profiles_router.get("", response_model=TeacherCardProfileListResponse)
def list_card_profiles(
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> TeacherCardProfileListResponse:
    rows = LearningProfileRepository(session).list_with_card_counts(teacher.id)
    profiles = [
        profile_to_response(profile, new_count, published_count) for profile, new_count, published_count in rows
    ]
    return TeacherCardProfileListResponse(profiles=profiles)


@router.get("", response_model=VocabularyCardListResponse)
def list_cards(
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
    profile_id: Annotated[int | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> VocabularyCardListResponse:
    cards = VocabularyCardRepository(session).list_for_teacher(
        teacher_user_id=teacher.id,
        learning_profile_id=profile_id,
        status=status_filter,
    )
    return VocabularyCardListResponse(cards=[card_to_response(card) for card in cards])


@router.post("", response_model=VocabularyCardRead)
def create_card(
    payload: VocabularyCardCreate,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> VocabularyCardRead:
    get_teacher_profile_or_404(session, teacher, payload.learning_profile_id)
    card = VocabularyCardRepository(session).create_manual_draft_card(teacher.id, payload)
    session.commit()
    return card_to_response(card)


@router.patch("/{card_id}", response_model=VocabularyCardRead)
def update_card(
    card_id: int,
    payload: VocabularyCardUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> VocabularyCardRead:
    repository = VocabularyCardRepository(session)
    card = repository.get_for_teacher(teacher.id, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    card = repository.update_card(card, payload)
    session.commit()
    return card_to_response(card)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(
    card_id: int,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> Response:
    repository = VocabularyCardRepository(session)
    card = repository.get_for_teacher(teacher.id, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    repository.delete_card(card)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/publish-batch", response_model=BatchPublishCardsResponse)
def publish_batch(
    payload: BatchPublishCardsRequest,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> BatchPublishCardsResponse:
    get_teacher_profile_or_404(session, teacher, payload.learning_profile_id)
    published_count = VocabularyCardRepository(session).publish_draft_cards_for_profile(
        teacher_user_id=teacher.id,
        learning_profile_id=payload.learning_profile_id,
    )
    session.commit()
    return BatchPublishCardsResponse(published_count=published_count)


@router.post("/{card_id}/publish", response_model=VocabularyCardRead)
def publish_card(
    card_id: int,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> VocabularyCardRead:
    return _set_card_status(session=session, teacher=teacher, card_id=card_id, card_status="published")


@router.post("/{card_id}/archive", response_model=VocabularyCardRead)
def archive_card(
    card_id: int,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> VocabularyCardRead:
    return _set_card_status(session=session, teacher=teacher, card_id=card_id, card_status="archived")


def _set_card_status(session: Session, teacher: User, card_id: int, card_status: str) -> VocabularyCardRead:
    repository = VocabularyCardRepository(session)
    card = repository.get_for_teacher(teacher.id, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    card = repository.set_status(card, card_status)
    session.commit()
    return card_to_response(card)
