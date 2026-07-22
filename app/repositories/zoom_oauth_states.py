from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ZoomOAuthState


class ZoomOAuthStateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, user_id: int, ttl_minutes: int) -> ZoomOAuthState:
        state = ZoomOAuthState(
            user_id=user_id,
            state=token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
        )
        self.session.add(state)
        self.session.flush()
        return state

    def get_valid(self, state_token: str) -> ZoomOAuthState | None:
        return self.session.scalar(
            select(ZoomOAuthState).where(
                ZoomOAuthState.state == state_token,
                ZoomOAuthState.consumed_at.is_(None),
                ZoomOAuthState.expires_at > datetime.now(UTC),
            )
        )

    def mark_consumed(self, state: ZoomOAuthState) -> None:
        state.consumed_at = datetime.now(UTC)
        self.session.flush()
