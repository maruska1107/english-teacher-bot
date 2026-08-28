import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.services.lesson_processing import LessonProcessingService
from app.telegram.messages import ZOOM_CONNECTED_TEXT, ZOOM_CONNECTED_WEBAPP_TEXT
from app.telegram.notifier import TelegramBotNotifier, TelegramNotifierProtocol
from app.zoom.oauth import ZoomOAuthClient, ZoomOAuthClientProtocol, ZoomOAuthService
from app.zoom.webhook_security import encrypted_url_validation_token, verify_zoom_webhook_signature
from app.zoom.webhooks import ZoomWebhookService

router = APIRouter(prefix="/api/zoom", tags=["zoom"])


def get_zoom_oauth_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ZoomOAuthClientProtocol:
    return ZoomOAuthClient(settings)


def get_telegram_notifier(
    settings: Annotated[Settings, Depends(get_settings)],
) -> TelegramNotifierProtocol:
    return TelegramBotNotifier(settings)


def get_lesson_processing_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LessonProcessingService:
    return LessonProcessingService(session=session, settings=settings)


@router.get("/oauth/callback")
async def zoom_oauth_callback(
    code: Annotated[str, Query(min_length=1)],
    state: Annotated[str, Query(min_length=1)],
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[ZoomOAuthClientProtocol, Depends(get_zoom_oauth_client)],
    notifier: Annotated[TelegramNotifierProtocol, Depends(get_telegram_notifier)],
) -> dict[str, str]:
    service = ZoomOAuthService(session=session, settings=settings)
    try:
        token = await service.complete_oauth_callback(code=code, state_token=state, client=client)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        ) from exc
    await notifier.send_message(token.user.telegram_user_id, ZOOM_CONNECTED_TEXT)
    await notifier.send_webapp_button(
        token.user.telegram_user_id,
        ZOOM_CONNECTED_WEBAPP_TEXT,
        "Открыть кабинет",
        "https://englishtutorai.ru/teacher/cards",
    )
    return {"status": "connected"}


@router.post("/webhook")
async def zoom_webhook(
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    lesson_processor: Annotated[LessonProcessingService, Depends(get_lesson_processing_service)],
    x_zm_request_timestamp: Annotated[str | None, Header()] = None,
    x_zm_signature: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    raw_body = await request.body()
    payload = json.loads(raw_body)
    event_type = payload.get("event")

    if event_type == "endpoint.url_validation":
        plain_token = payload["payload"]["plainToken"]
        assert settings.zoom_webhook_secret_token is not None
        return {
            "plainToken": plain_token,
            "encryptedToken": encrypted_url_validation_token(
                settings.zoom_webhook_secret_token.get_secret_value(),
                plain_token,
            ),
        }

    body = await verify_zoom_webhook_signature(
        request=request,
        settings=settings,
        x_zm_request_timestamp=x_zm_request_timestamp,
        x_zm_signature=x_zm_signature,
    )
    payload = json.loads(body)
    event_type = payload.get("event")

    if event_type in {"recording.completed", "recording.transcript_completed"}:
        result = ZoomWebhookService(session).handle_recording_completed(payload)
        if settings.auto_process_zoom_webhook_lessons and result.lesson is not None:
            await lesson_processor.process_lesson(result.lesson.id, zoom_download_token=result.download_token)
        return {"status": result.status}

    return {"status": "ignored"}
