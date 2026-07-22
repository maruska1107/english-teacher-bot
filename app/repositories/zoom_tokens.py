from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import ZoomToken


class ZoomTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def delete_for_user(self, user_id: int) -> int:
        result = self.session.execute(delete(ZoomToken).where(ZoomToken.user_id == user_id))
        return result.rowcount or 0
