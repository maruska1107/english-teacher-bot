import logging
from collections.abc import AsyncGenerator
from typing import Annotated, Any, Protocol
from urllib.parse import quote

import httpx
from fastapi import Depends
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import VocabularyCard
from app.repositories.vocabulary_cards import VocabularyCardRepository
from app.schemas.cards import CardImageCandidate

logger = logging.getLogger(__name__)

# Openverse accepts longer searches, but 300 characters keeps generated card context
# safely bounded while retaining enough English context for useful results.
MAX_IMAGE_QUERY_LENGTH = 300
_MAX_OPENVERSE_PAGE_SIZE = 50


class OpenverseImageClientProtocol(Protocol):
    async def search(self, query: str, offset: int = 0, limit: int = 3) -> list[CardImageCandidate]: ...

    async def get(self, image_id: str) -> CardImageCandidate | None: ...


def build_image_query(card: VocabularyCard) -> str:
    """Build a bounded query from the normalized term only; never include card context."""
    return " ".join(card.term.split())[:MAX_IMAGE_QUERY_LENGTH].rstrip()


class OpenverseImageClient:
    def __init__(self, settings: Settings, async_client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self._owns_async_client = async_client is None
        self._async_client = async_client or httpx.AsyncClient()
        self._base_url = settings.openverse_api_base_url

    async def __aenter__(self) -> "OpenverseImageClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_async_client:
            await self._async_client.aclose()

    async def search(self, query: str, offset: int = 0, limit: int = 3) -> list[CardImageCandidate]:
        page_size = self._clamp_limit(limit)
        params = {
            "q": query,
            "page_size": page_size,
            "page": max(0, offset) // page_size + 1,
            "license_type": "commercial",
            "license": "cc0,pdm,by,by-sa",
        }
        payload = await self._request_json(f"{self._base_url}/images/", params=params)
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            if payload is not None:
                logger.warning("Openverse search returned an invalid payload")
            return []

        candidates: list[CardImageCandidate] = []
        for result in payload["results"][:page_size]:
            candidate = self._parse_candidate(result)
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    async def get(self, image_id: str) -> CardImageCandidate | None:
        normalized_id = image_id.strip() if isinstance(image_id, str) else ""
        if not normalized_id or len(normalized_id) > 100:
            return None
        encoded_id = quote(normalized_id, safe="")
        payload = await self._request_json(f"{self._base_url}/images/{encoded_id}/")
        return self._parse_candidate(payload)

    def _clamp_limit(self, limit: int) -> int:
        configured_maximum = min(max(1, self.settings.openverse_result_page_size), _MAX_OPENVERSE_PAGE_SIZE)
        return min(max(1, limit), configured_maximum)

    async def _request_json(self, url: str, params: dict[str, Any] | None = None) -> Any | None:
        request_kwargs = {
            "headers": {"User-Agent": self.settings.openverse_user_agent},
            "timeout": self.settings.openverse_timeout_seconds,
            "params": params,
        }
        try:
            response = await self._async_client.get(url, **request_kwargs)
        except httpx.HTTPError as exc:
            logger.warning("Openverse request failed: %s", type(exc).__name__)
            return None

        if not response.is_success:
            logger.warning("Openverse request returned HTTP %s", response.status_code)
            return None
        try:
            return response.json()
        except ValueError:
            logger.warning("Openverse response was not valid JSON")
            return None

    @staticmethod
    def _parse_candidate(payload: Any) -> CardImageCandidate | None:
        if not isinstance(payload, dict):
            return None
        try:
            return CardImageCandidate(
                image_id=payload.get("id"),
                image_url=payload.get("thumbnail") or payload.get("url"),
                source_url=payload.get("foreign_landing_url"),
                creator=payload.get("creator"),
                license=payload.get("license"),
                license_url=payload.get("license_url"),
            )
        except (ValidationError, TypeError):
            return None


async def enrich_card_image(
    session: Session,
    card: VocabularyCard,
    settings: Settings,
    client: OpenverseImageClientProtocol,
    query: str | None = None,
) -> bool:
    if not settings.openverse_images_enabled:
        return False

    query = build_image_query(card) if query is None else query
    if not query:
        return False

    lookup_query, candidate = await lookup_card_image(query, settings, client)
    return persist_card_image_result(session, card, lookup_query, candidate)


async def lookup_card_image(
    query: str,
    settings: Settings,
    client: OpenverseImageClientProtocol,
) -> tuple[str, CardImageCandidate | None]:
    """Perform external lookup only, without reading or mutating ORM/session state."""
    if not settings.openverse_images_enabled or not query:
        return query, None
    try:
        candidates = await client.search(query, limit=1)
        return query, candidates[0] if candidates else None
    except Exception as exc:
        logger.warning("Card image enrichment failed: %s", type(exc).__name__)
        return query, None


def persist_card_image_result(
    session: Session,
    card: VocabularyCard,
    query: str,
    candidate: CardImageCandidate | None,
) -> bool:
    """Persist one optional lookup result and restore session usability on DB failure."""
    try:
        if candidate is None:
            card.image_search_query = query
            session.flush()
        else:
            VocabularyCardRepository(session).set_image(card, candidate, query)
        session.commit()
        return candidate is not None
    except SQLAlchemyError as exc:
        logger.warning("Card image metadata persistence failed: %s", type(exc).__name__)
        session.rollback()
        return False


async def get_openverse_image_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncGenerator[OpenverseImageClient, None]:
    """FastAPI-overridable request dependency for Openverse image operations."""
    async with OpenverseImageClient(settings) as client:
        yield client
