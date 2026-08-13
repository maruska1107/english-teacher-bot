from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import User, ZoomToken
from app.repositories.zoom_oauth_states import ZoomOAuthStateRepository

ZOOM_AUTHORIZE_URL = "https://zoom.us/oauth/authorize"
ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"
ZOOM_CURRENT_USER_URL = "https://api.zoom.us/v2/users/me"


@dataclass(frozen=True)
class ZoomTokenPayload:
    access_token: str
    refresh_token: str
    expires_in: int


@dataclass(frozen=True)
class ZoomUserProfile:
    zoom_user_id: str
    zoom_account_id: str


class ZoomOAuthClientProtocol(Protocol):
    async def exchange_code_for_token(self, code: str) -> ZoomTokenPayload: ...

    async def refresh_access_token(self, refresh_token: str) -> ZoomTokenPayload: ...

    async def get_current_user(self, access_token: str) -> ZoomUserProfile: ...


class ZoomOAuthClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def exchange_code_for_token(self, code: str) -> ZoomTokenPayload:
        if self.settings.zoom_client_id is None or self.settings.zoom_client_secret is None:
            raise RuntimeError("Zoom OAuth client credentials are not configured")

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                ZOOM_TOKEN_URL,
                auth=(self.settings.zoom_client_id, self.settings.zoom_client_secret.get_secret_value()),
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.settings.zoom_redirect_uri,
                },
            )
            response.raise_for_status()
            payload = response.json()

        return ZoomTokenPayload(
            access_token=payload["access_token"],
            refresh_token=payload["refresh_token"],
            expires_in=int(payload.get("expires_in", 3600)),
        )

    async def get_current_user(self, access_token: str) -> ZoomUserProfile:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                ZOOM_CURRENT_USER_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            payload = response.json()

        return ZoomUserProfile(
            zoom_user_id=payload["id"],
            zoom_account_id=payload.get("account_id") or payload.get("accountId") or "",
        )

    async def refresh_access_token(self, refresh_token: str) -> ZoomTokenPayload:
        if self.settings.zoom_client_id is None or self.settings.zoom_client_secret is None:
            raise RuntimeError("Zoom OAuth client credentials are not configured")

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                ZOOM_TOKEN_URL,
                auth=(self.settings.zoom_client_id, self.settings.zoom_client_secret.get_secret_value()),
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
            payload = response.json()

        return ZoomTokenPayload(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token") or refresh_token,
            expires_in=int(payload.get("expires_in", 3600)),
        )


class ZoomOAuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.states = ZoomOAuthStateRepository(session)

    def build_authorization_url(self, user: User) -> str:
        if not self.settings.zoom_client_id or not self.settings.zoom_redirect_uri:
            raise RuntimeError("Zoom OAuth settings are not configured")

        state = self.states.create(
            user_id=user.id,
            ttl_minutes=self.settings.zoom_oauth_state_ttl_minutes,
        )
        self.session.commit()
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.settings.zoom_client_id,
                "redirect_uri": self.settings.zoom_redirect_uri,
                "state": state.state,
            }
        )
        return f"{ZOOM_AUTHORIZE_URL}?{query}"

    async def complete_oauth_callback(
        self,
        code: str,
        state_token: str,
        client: ZoomOAuthClientProtocol,
    ) -> ZoomToken:
        state = self.states.get_valid(state_token)
        if state is None:
            raise ValueError("Invalid or expired OAuth state")

        token_payload = await client.exchange_code_for_token(code)
        zoom_user = await client.get_current_user(token_payload.access_token)
        expires_at = datetime.now(UTC) + timedelta(seconds=token_payload.expires_in)

        token = self.session.scalar(
            select(ZoomToken).where(
                ZoomToken.user_id == state.user_id,
                ZoomToken.zoom_user_id == zoom_user.zoom_user_id,
            )
        )
        if token is None:
            token = ZoomToken(
                user_id=state.user_id,
                zoom_account_id=zoom_user.zoom_account_id,
                zoom_user_id=zoom_user.zoom_user_id,
                access_token=token_payload.access_token,
                refresh_token=token_payload.refresh_token,
                expires_at=expires_at,
            )
            self.session.add(token)
        else:
            token.zoom_account_id = zoom_user.zoom_account_id
            token.access_token = token_payload.access_token
            token.refresh_token = token_payload.refresh_token
            token.expires_at = expires_at

        self.states.mark_consumed(state)
        self.session.commit()
        return token
