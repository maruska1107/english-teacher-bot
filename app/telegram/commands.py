import re
from typing import Protocol
from urllib.parse import parse_qs, urlparse

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories.lessons import LessonRepository
from app.repositories.users import UserRepository
from app.repositories.zoom_meeting_subscriptions import ZoomMeetingSubscriptionRepository
from app.repositories.zoom_tokens import ZoomTokenRepository
from app.telegram.messages import (
    ACCESS_DENIED_TEXT,
    ADMIN_ONLY_TEXT,
    NO_ERRORS_TEXT,
    NO_REPORTS_TEXT,
    START_NOTICE_TEXT,
    ZOOM_CONNECT_NOT_READY_TEXT,
    ZOOM_DISCONNECTED_TEXT,
    ZOOM_MEETING_LINK_HELP_TEXT,
    ZOOM_MEETING_SUBSCRIBED_TEMPLATE,
)
from app.zoom.oauth import ZoomOAuthService


class TelegramGateway(Protocol):
    async def send_message(self, chat_id: int, text: str) -> None: ...


def extract_zoom_meeting_id(meeting_link: str) -> str | None:
    value = meeting_link.strip()
    if not value:
        return None

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https", "zoommtg"}:
        return None
    host = parsed.netloc.lower()
    if "zoom.us" not in host:
        return None

    query = parse_qs(parsed.query)
    for key in ("confno", "meeting_id"):
        if key in query:
            digits = re.sub(r"\D", "", query[key][0])
            return digits if len(digits) >= 6 else None

    match = re.search(r"/(?:j|s|wc/join)/(\d{6,})", parsed.path)
    if match:
        return match.group(1)

    return None


class TelegramCommandService:
    """Business logic for Telegram commands.

    The service is intentionally independent from python-telegram-bot Update objects
    so command behavior can be tested without network calls.
    """

    def __init__(self, session: Session, gateway: TelegramGateway, settings: Settings) -> None:
        self.session = session
        self.gateway = gateway
        self.settings = settings
        self.users = UserRepository(session)
        self.lessons = LessonRepository(session)
        self.zoom_meeting_subscriptions = ZoomMeetingSubscriptionRepository(session)
        self.zoom_tokens = ZoomTokenRepository(session)

    async def handle_start(self, telegram_user_id: int, chat_id: int) -> None:
        if not self._is_allowed_teacher(telegram_user_id):
            await self.gateway.send_message(chat_id, ACCESS_DENIED_TEXT)
            return

        self.users.get_or_create_teacher(telegram_user_id)
        self.session.commit()
        await self.gateway.send_message(chat_id, START_NOTICE_TEXT)

    async def handle_connect_zoom(self, telegram_user_id: int, chat_id: int) -> None:
        if not await self._ensure_allowed_teacher(telegram_user_id, chat_id):
            return
        user = self.users.get_by_telegram_id(telegram_user_id)
        assert user is not None
        try:
            authorization_url = ZoomOAuthService(
                session=self.session,
                settings=self.settings,
            ).build_authorization_url(user)
        except RuntimeError:
            await self.gateway.send_message(chat_id, ZOOM_CONNECT_NOT_READY_TEXT)
            return
        await self.gateway.send_message(chat_id, f"Подключите Zoom по ссылке:\n{authorization_url}")

    async def handle_add_zoom_meeting(self, telegram_user_id: int, chat_id: int, meeting_link: str = "") -> None:
        if not await self._ensure_allowed_teacher(telegram_user_id, chat_id):
            return
        meeting_id = extract_zoom_meeting_id(meeting_link)
        if meeting_id is None:
            await self.gateway.send_message(chat_id, ZOOM_MEETING_LINK_HELP_TEXT)
            return
        user = self.users.get_by_telegram_id(telegram_user_id)
        assert user is not None
        self.zoom_meeting_subscriptions.upsert_for_user(
            user_id=user.id,
            meeting_id=meeting_id,
            meeting_url=meeting_link.strip(),
        )
        self.session.commit()
        await self.gateway.send_message(
            chat_id,
            ZOOM_MEETING_SUBSCRIBED_TEMPLATE.format(meeting_id=meeting_id),
        )

    async def handle_disconnect_zoom(self, telegram_user_id: int, chat_id: int) -> None:
        if not await self._ensure_allowed_teacher(telegram_user_id, chat_id):
            return
        user = self.users.get_by_telegram_id(telegram_user_id)
        assert user is not None
        self.zoom_tokens.delete_for_user(user.id)
        self.session.commit()
        await self.gateway.send_message(chat_id, ZOOM_DISCONNECTED_TEXT)

    async def handle_status(self, telegram_user_id: int, chat_id: int) -> None:
        if not await self._ensure_allowed_user_or_admin(telegram_user_id, chat_id):
            return

        user = self.users.get_by_telegram_id(telegram_user_id)
        if user is None and telegram_user_id == self.settings.telegram_admin_id:
            total_lessons = self.lessons.count_all_completed()
            await self.gateway.send_message(
                chat_id,
                "Статус бота\n"
                "Пользователь: администратор\n"
                "Zoom: не применимо\n"
                f"Обработано уроков: {total_lessons}",
            )
            return

        assert user is not None
        zoom_status = "подключён" if self.lessons.has_zoom_connection(user.id) else "не подключён"
        completed_count = self.lessons.count_completed_for_teacher(user.id)
        await self.gateway.send_message(
            chat_id,
            "Статус бота\n" "Пользователь: активен\n" f"Zoom: {zoom_status}\n" f"Обработано уроков: {completed_count}",
        )

    async def handle_last_report(self, telegram_user_id: int, chat_id: int) -> None:
        if not await self._ensure_allowed_user_or_admin(telegram_user_id, chat_id):
            return

        user = self.users.get_by_telegram_id(telegram_user_id)
        if user is None:
            if telegram_user_id == self.settings.telegram_admin_id:
                analysis = self.lessons.latest_analysis()
            else:
                await self.gateway.send_message(chat_id, NO_REPORTS_TEXT)
                return
        else:
            analysis = self.lessons.latest_analysis_for_teacher(user.id)

        if analysis is None:
            await self.gateway.send_message(chat_id, NO_REPORTS_TEXT)
            return

        await self.gateway.send_message(
            chat_id,
            "Последний отчёт\n\n"
            f"{analysis.teacher_report}\n\n"
            "Сообщение для учеников\n"
            f"{analysis.student_message}",
        )

    async def handle_last_error(self, telegram_user_id: int, chat_id: int) -> None:
        if telegram_user_id != self.settings.telegram_admin_id:
            await self.gateway.send_message(chat_id, ADMIN_ONLY_TEXT)
            return

        error = self.lessons.latest_processing_error()
        await self.gateway.send_message(chat_id, f"Последняя ошибка\n{error}" if error else NO_ERRORS_TEXT)

    def _is_allowed_teacher(self, telegram_user_id: int) -> bool:
        return telegram_user_id in self.settings.allowed_teacher_ids

    async def _ensure_allowed_teacher(self, telegram_user_id: int, chat_id: int) -> bool:
        if self._is_allowed_teacher(telegram_user_id):
            if self.users.get_by_telegram_id(telegram_user_id) is None:
                self.users.get_or_create_teacher(telegram_user_id)
                self.session.commit()
            return True
        await self.gateway.send_message(chat_id, ACCESS_DENIED_TEXT)
        return False

    async def _ensure_allowed_user_or_admin(self, telegram_user_id: int, chat_id: int) -> bool:
        if telegram_user_id == self.settings.telegram_admin_id or self._is_allowed_teacher(telegram_user_id):
            return True
        await self.gateway.send_message(chat_id, ACCESS_DENIED_TEXT)
        return False
