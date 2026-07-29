from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        return self.session.scalar(select(User).where(User.telegram_user_id == telegram_user_id))

    def get_or_create_teacher(self, telegram_user_id: int) -> User:
        user = self.get_by_telegram_id(telegram_user_id)
        if user is not None:
            if not user.is_active:
                user.is_active = True
            return user

        user = User(telegram_user_id=telegram_user_id, role="teacher", is_active=True)
        self.session.add(user)
        self.session.flush()
        return user
