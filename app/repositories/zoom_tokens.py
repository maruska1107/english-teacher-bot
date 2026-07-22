from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ZoomToken


class ZoomTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_teacher_id_for_zoom_host(self, zoom_user_id: str, zoom_account_id: str | None) -> int | None:
        query = select(ZoomToken.user_id).where(ZoomToken.zoom_user_id == zoom_user_id)
        if zoom_account_id:
            query = query.where(ZoomToken.zoom_account_id == zoom_account_id)
        return self.session.scalar(query)

    def get_for_user(self, user_id: int) -> ZoomToken | None:
        return self.session.scalar(select(ZoomToken).where(ZoomToken.user_id == user_id).limit(1))

    def delete_for_user(self, user_id: int) -> int:
        tokens = self.session.scalars(select(ZoomToken).where(ZoomToken.user_id == user_id)).all()
        for token in tokens:
            self.session.delete(token)
        self.session.flush()
        return len(tokens)
