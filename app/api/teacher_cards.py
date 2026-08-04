import logging
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from pydantic import ConfigDict
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
    CardImageOptionsResponse,
    CardImageSelection,
    TeacherCardProfileListResponse,
    TeacherCardProfileRead,
    VocabularyCardCreate,
    VocabularyCardListResponse,
    VocabularyCardRead,
    VocabularyCardUpdate,
)
from app.services.openverse_images import (
    OpenverseImageClient,
    OpenverseOperationStatus,
    TeacherOpenverseImageClientProtocol,
    build_image_query,
    enrich_card_image,
    get_openverse_image_client,
)
from app.telegram.webapp_auth import TelegramWebAppAuthError, verify_telegram_webapp_init_data

router = APIRouter(prefix="/api/teacher/cards", tags=["teacher-cards"])
profiles_router = APIRouter(prefix="/api/teacher/card-profiles", tags=["teacher-card-profiles"])
logger = logging.getLogger(__name__)


class StrictCardImageSelection(CardImageSelection):
    model_config = ConfigDict(extra="forbid")


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
        image_url=card.image_url,
        image_source_url=card.image_source_url,
        image_creator=card.image_creator,
        image_license=card.image_license,
        image_license_url=card.image_license_url,
        image_search_query=card.image_search_query,
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
    teacher = UserRepository(session).get_by_telegram_id(telegram_user_id)
    if teacher is None:
        if telegram_user_id not in settings.allowed_teacher_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher is not allowed")
        teacher = UserRepository(session).get_or_create_teacher(telegram_user_id)
        session.commit()
    if telegram_user_id not in settings.allowed_teacher_ids and not settings.zoom_review_access_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher is not allowed")
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


def get_teacher_draft_card_or_error(session: Session, teacher: User | int, card_id: int) -> VocabularyCard:
    teacher_id = teacher if isinstance(teacher, int) else teacher.id
    card = VocabularyCardRepository(session).get_for_teacher(teacher_id, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    if card.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only draft cards can change images")
    return card


def _validated_persisted_https_url(value: str | None) -> str | None:
    if not value or len(value) > 2048:
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    return value if parsed.scheme == "https" and bool(parsed.hostname) else None


def _raise_for_teacher_provider_status(provider_status: OpenverseOperationStatus) -> None:
    if provider_status is OpenverseOperationStatus.UNAVAILABLE:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Image provider unavailable")
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Image is unavailable")


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
async def create_card(
    payload: VocabularyCardCreate,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
    settings: Annotated[Settings, Depends(get_settings)],
    image_client: Annotated[OpenverseImageClient, Depends(get_openverse_image_client)],
) -> VocabularyCardRead:
    get_teacher_profile_or_404(session, teacher, payload.learning_profile_id)
    card = VocabularyCardRepository(session).create_manual_draft_card(teacher.id, payload)
    image_query = build_image_query(card)
    session.commit()
    await enrich_card_image(session, card, settings, image_client, query=image_query)
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


@router.get("/{card_id}/image-options", response_model=CardImageOptionsResponse)
async def list_card_image_options(
    card_id: int,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
    image_client: Annotated[TeacherOpenverseImageClientProtocol, Depends(get_openverse_image_client)],
    offset: Annotated[int, Query()] = 0,
) -> CardImageOptionsResponse:
    teacher_id = teacher.id
    card = get_teacher_draft_card_or_error(session, teacher_id, card_id)
    clamped_offset = min(max(offset, 0), 300)
    query = card.image_search_query or build_image_query(card)
    current_image_url = _validated_persisted_https_url(card.image_url)
    current_source_url = _validated_persisted_https_url(card.image_source_url)
    session.rollback()

    options = []
    seen_image_ids: set[str] = set()
    seen_image_urls: set[str] = set()
    seen_source_urls: set[str] = set()
    page_offset = clamped_offset
    pages_consumed = 0
    while page_offset <= 300 and pages_consumed < 5 and len(options) < 3:
        try:
            result = await image_client.search_strict(query, offset=page_offset, limit=3)
        except Exception as exc:
            logger.warning("Teacher image options lookup failed: %s", type(exc).__name__)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Image provider unavailable") from exc

        get_teacher_draft_card_or_error(session, teacher_id, card_id)
        pages_consumed += 1
        page_offset += 3
        if result.status is not OpenverseOperationStatus.OK:
            _raise_for_teacher_provider_status(result.status)
        candidates = result.value or []
        for candidate in candidates:
            if candidate.image_url == current_image_url or candidate.source_url == current_source_url:
                continue
            if (
                candidate.image_id in seen_image_ids
                or candidate.image_url in seen_image_urls
                or candidate.source_url in seen_source_urls
            ):
                continue
            seen_image_ids.add(candidate.image_id)
            seen_image_urls.add(candidate.image_url)
            seen_source_urls.add(candidate.source_url)
            options.append(candidate)
            if len(options) == 3:
                break
        if not candidates or len(options) == 3 or page_offset > 300:
            break
        session.rollback()

    session.rollback()
    if not options:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No suitable images found")
    return CardImageOptionsResponse(options=options, next_offset=page_offset)


@router.put("/{card_id}/image", response_model=VocabularyCardRead)
async def select_card_image(
    card_id: int,
    payload: StrictCardImageSelection,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
    image_client: Annotated[TeacherOpenverseImageClientProtocol, Depends(get_openverse_image_client)],
) -> VocabularyCardRead:
    teacher_id = teacher.id
    card = get_teacher_draft_card_or_error(session, teacher_id, card_id)
    query = card.image_search_query or build_image_query(card)
    session.rollback()
    try:
        result = await image_client.get_strict(payload.image_id)
    except Exception as exc:
        logger.warning("Teacher image selection lookup failed: %s", type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Image provider unavailable") from exc
    card = get_teacher_draft_card_or_error(session, teacher_id, card_id)
    candidate = result.value
    if result.status is not OpenverseOperationStatus.OK or candidate is None:
        _raise_for_teacher_provider_status(result.status)
    assert candidate is not None
    VocabularyCardRepository(session).set_image(card, candidate, query)
    session.commit()
    return card_to_response(card)


@router.delete("/{card_id}/image", response_model=VocabularyCardRead)
def clear_card_image(
    card_id: int,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> VocabularyCardRead:
    card = get_teacher_draft_card_or_error(session, teacher, card_id)
    VocabularyCardRepository(session).clear_image(card)
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
