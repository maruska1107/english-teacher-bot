from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.zoom.oauth import ZoomOAuthClient, ZoomOAuthClientProtocol, ZoomOAuthService

router = APIRouter(prefix="/api/zoom", tags=["zoom"])


def get_zoom_oauth_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ZoomOAuthClientProtocol:
    return ZoomOAuthClient(settings)


@router.get("/oauth/callback")
async def zoom_oauth_callback(
    code: Annotated[str, Query(min_length=1)],
    state: Annotated[str, Query(min_length=1)],
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[ZoomOAuthClientProtocol, Depends(get_zoom_oauth_client)],
) -> dict[str, str]:
    service = ZoomOAuthService(session=session, settings=settings)
    try:
        await service.complete_oauth_callback(code=code, state_token=state, client=client)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        ) from exc
    return {"status": "connected"}
