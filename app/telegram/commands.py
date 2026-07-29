import re
from typing import Protocol
from urllib.parse import parse_qs, urlparse

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import LearningProfile, LearningProfileMember, Lesson, LessonAnalysis, Student, VocabularyCard
from app.repositories.learning_profiles import LearningProfileRepository
from app.repositories.lessons import LessonRepository
from app.repositories.students import StudentRepository
from app.repositories.users import UserRepository
from app.repositories.zoom_meeting_subscriptions import ZoomMeetingSubscriptionRepository
from app.repositories.zoom_tokens import ZoomTokenRepository
from app.telegram.invites import build_student_invite_link, generate_invite_token, hash_invite_token
from app.telegram.messages import (
    ACCESS_DENIED_TEMPLATE,
    ADMIN_ONLY_TEXT,
    CARD_REVIEW_WEBAPP_TEXT,
    NO_ERRORS_TEXT,
    NO_REPORTS_TEXT,
    START_NOTICE_TEXT,
    STUDENT_CARDS_WEBAPP_TEXT,
    ZOOM_CONNECT_NOT_READY_TEXT,
    ZOOM_DISCONNECTED_TEXT,
    ZOOM_MEETING_LINK_HELP_TEXT,
    ZOOM_MEETING_SUBSCRIBED_TEMPLATE,
)
from app.zoom.oauth import ZoomOAuthService


class TelegramGateway(Protocol):
    async def send_message(self, chat_id: int, text: str) -> None: ...

    async def send_webapp_button(self, chat_id: int, text: str, button_text: str, webapp_url: str) -> None: ...


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
        self.students = StudentRepository(session)
        self.learning_profiles = LearningProfileRepository(session)
        self.lessons = LessonRepository(session)
        self.zoom_meeting_subscriptions = ZoomMeetingSubscriptionRepository(session)
        self.zoom_tokens = ZoomTokenRepository(session)

    async def handle_start(self, telegram_user_id: int, chat_id: int, start_payload: str = "") -> None:
        if start_payload.startswith("student_"):
            await self._handle_student_invite_start(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                raw_token=start_payload.removeprefix("student_"),
            )
            return
        linked_student = self.students.get_by_telegram_user_id(telegram_user_id)
        if linked_student is not None:
            await self._send_student_cards_button(chat_id, linked_student.name)
            return
        if not self._is_allowed_teacher(telegram_user_id):
            await self._send_access_denied(chat_id, telegram_user_id)
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
        meeting_url, profile_name = self._parse_meeting_profile_spec(meeting_link)
        meeting_id = extract_zoom_meeting_id(meeting_url)
        if meeting_id is None:
            await self.gateway.send_message(chat_id, ZOOM_MEETING_LINK_HELP_TEXT)
            return
        user = self.users.get_by_telegram_id(telegram_user_id)
        assert user is not None
        learning_profile_id = None
        if profile_name is not None:
            profile = self.learning_profiles.get_by_teacher_and_name(user.id, profile_name)
            if profile is None:
                await self.gateway.send_message(chat_id, f"Учебный профиль не найден: {profile_name}")
                return
            learning_profile_id = profile.id
        self.zoom_meeting_subscriptions.upsert_for_user(
            user_id=user.id,
            meeting_id=meeting_id,
            meeting_url=meeting_url.strip(),
            learning_profile_id=learning_profile_id,
        )
        self.session.commit()
        message = ZOOM_MEETING_SUBSCRIBED_TEMPLATE.format(meeting_id=meeting_id)
        if profile_name is not None:
            message = f"{message}\n\nПрофиль: {profile_name}"
        await self.gateway.send_message(chat_id, message)

    async def handle_add_student(self, telegram_user_id: int, chat_id: int, student_name: str = "") -> None:
        if not await self._ensure_allowed_teacher(telegram_user_id, chat_id):
            return
        normalized_name = student_name.strip()
        if not normalized_name:
            await self.gateway.send_message(chat_id, "Пришлите имя ученика в формате:\n/add_student Анна")
            return
        user = self.users.get_by_telegram_id(telegram_user_id)
        assert user is not None
        profile, student = self.learning_profiles.create_individual_profile(
            teacher_user_id=user.id,
            student_name=normalized_name,
        )
        invite_link = self._refresh_student_invite_link(student)
        self.session.commit()
        await self.gateway.send_message(
            chat_id,
            f"Ученик создан ✅\n\nСсылка для ученика {student.name}:\n{invite_link}",
        )

    async def handle_add_group(self, telegram_user_id: int, chat_id: int, group_spec: str = "") -> None:
        if not await self._ensure_allowed_teacher(telegram_user_id, chat_id):
            return
        group_name, member_names = self._parse_group_spec(group_spec)
        if group_name is None or not member_names:
            await self.gateway.send_message(
                chat_id,
                "Пришлите группу в формате:\n/add_group Название группы: Анна, Мария",
            )
            return
        user = self.users.get_by_telegram_id(telegram_user_id)
        assert user is not None
        profile = self.learning_profiles.create_group_profile(
            teacher_user_id=user.id,
            profile_name=group_name,
            member_names=member_names,
        )
        invite_lines = []
        for member in sorted(profile.memberships, key=lambda profile_member: profile_member.student.name):
            invite_lines.append(f"{member.student.name}: {self._refresh_student_invite_link(member.student)}")
        self.session.commit()
        await self.gateway.send_message(
            chat_id,
            "Группа создана ✅\n\n" f"{profile.name}\n\n" "Ссылки для учеников:\n" + "\n".join(invite_lines),
        )

    async def handle_cards(self, telegram_user_id: int, chat_id: int) -> None:
        if not await self._ensure_allowed_teacher(telegram_user_id, chat_id):
            return
        self.users.get_or_create_teacher(telegram_user_id)
        self.session.commit()
        await self.gateway.send_webapp_button(
            chat_id,
            CARD_REVIEW_WEBAPP_TEXT,
            "Открыть WebApp",
            "https://englishtutorai.ru/teacher/cards",
        )

    async def handle_disconnect_zoom(self, telegram_user_id: int, chat_id: int) -> None:
        if not await self._ensure_allowed_teacher(telegram_user_id, chat_id):
            return
        user = self.users.get_by_telegram_id(telegram_user_id)
        assert user is not None
        self.zoom_tokens.delete_for_user(user.id)
        self.session.commit()
        await self.gateway.send_message(chat_id, ZOOM_DISCONNECTED_TEXT)

    async def handle_dev_seed_data(self, telegram_user_id: int, chat_id: int) -> None:
        if telegram_user_id != self.settings.telegram_admin_id:
            await self.gateway.send_message(chat_id, ADMIN_ONLY_TEXT)
            return
        teacher = self.users.get_or_create_teacher(telegram_user_id)
        self.session.flush()
        profile_name = "Тест Мария"

        existing_profile = self.learning_profiles.get_by_teacher_and_name(teacher.id, profile_name)
        if existing_profile is not None:
            for lesson in list(existing_profile.lessons):
                self.session.delete(lesson)
            for card in list(existing_profile.vocabulary_cards):
                self.session.delete(card)
            for membership in list(existing_profile.memberships):
                self.session.delete(membership)
            self.session.delete(existing_profile)
            self.session.flush()

        existing_student = self.students.get_by_telegram_user_id(telegram_user_id)
        if existing_student is not None and existing_student.teacher_user_id != teacher.id:
            existing_student.telegram_user_id = None
            self.session.flush()
        student = self.students.get_by_teacher_and_name(teacher.id, profile_name)
        if student is None:
            student = Student(teacher_user_id=teacher.id, name=profile_name)
            self.session.add(student)
            self.session.flush()
        student.telegram_user_id = telegram_user_id
        student.invite_status = "used"
        student.invite_token_hash = None

        profile = LearningProfile(
            teacher_user_id=teacher.id,
            name=profile_name,
            profile_type="individual",
            card_publish_mode="manual_review",
        )
        self.session.add(profile)
        self.session.flush()
        self.session.add(LearningProfileMember(learning_profile_id=profile.id, student_id=student.id))
        self.session.flush()

        lessons = []
        for index in range(1, 3):
            lesson = Lesson(
                teacher_user_id=teacher.id,
                learning_profile_id=profile.id,
                meeting_id=f"dev-meeting-{index}",
                meeting_uuid=f"dev-seed-{telegram_user_id}-{index}",
                processing_status="completed",
            )
            self.session.add(lesson)
            self.session.flush()
            self.session.add(
                LessonAnalysis(
                    lesson_id=lesson.id,
                    analysis_json={"summary": f"Тестовый урок {index}"},
                    teacher_report=f"Тестовый отчёт по уроку {index}.",
                    student_message=f"Сообщение ученику по тестовому уроку {index}.",
                    model="dev-seed",
                    prompt_version="dev-seed-v1",
                )
            )
            lessons.append(lesson)

        seed_cards = [
            ("journey", "путешествие", "published", lessons[0].id),
            ("improve", "улучшать", "published", lessons[0].id),
            ("fluency", "беглость речи", "draft", lessons[1].id),
            ("make progress", "делать успехи", "draft", lessons[1].id),
        ]
        for term, translation, card_status, lesson_id in seed_cards:
            self.session.add(
                VocabularyCard(
                    teacher_user_id=teacher.id,
                    learning_profile_id=profile.id,
                    lesson_id=lesson_id,
                    term=term,
                    translation_ru=translation,
                    example_sentence=f"Test example with {term}.",
                    status=card_status,
                )
            )

        self.session.commit()
        await self.gateway.send_message(
            chat_id,
            "Тестовые данные готовы ✅\n\n"
            "Профиль: Тест Мария\n"
            "Уроков: 2\n"
            "Draft-карточек: 2\n"
            "Published-карточек: 2\n\n"
            "Откройте /cards для преподавательского WebApp или /start для ученического WebApp.",
        )

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

    def _refresh_student_invite_link(self, student) -> str:
        raw_token = generate_invite_token()
        student.invite_token_hash = hash_invite_token(raw_token)
        student.invite_status = "active"
        return build_student_invite_link(self.settings.telegram_bot_username, raw_token)

    def _parse_group_spec(self, group_spec: str) -> tuple[str | None, list[str]]:
        if ":" not in group_spec:
            return None, []
        group_name, raw_members = group_spec.split(":", 1)
        member_names = []
        seen_names = set()
        for raw_name in raw_members.split(","):
            name = raw_name.strip()
            if name and name not in seen_names:
                member_names.append(name)
                seen_names.add(name)
        return group_name.strip() or None, member_names

    def _parse_meeting_profile_spec(self, meeting_link: str) -> tuple[str, str | None]:
        if "|" not in meeting_link:
            return meeting_link.strip(), None
        meeting_url, profile_name = meeting_link.split("|", 1)
        normalized_profile_name = profile_name.strip()
        return meeting_url.strip(), normalized_profile_name or None

    async def _handle_student_invite_start(self, telegram_user_id: int, chat_id: int, raw_token: str) -> None:
        student = self.students.get_by_invite_token_hash(hash_invite_token(raw_token))
        if student is None:
            await self.gateway.send_message(
                chat_id,
                "Ссылка недействительна или устарела. Попросите преподавателя отправить новую ссылку.",
            )
            return
        student.telegram_user_id = telegram_user_id
        student.invite_status = "used"
        self.session.commit()
        await self._send_student_cards_button(chat_id, student.name)

    async def _send_student_cards_button(self, chat_id: int, student_name: str) -> None:
        await self.gateway.send_webapp_button(
            chat_id,
            STUDENT_CARDS_WEBAPP_TEXT.format(student_name=student_name),
            "Открыть карточки",
            "https://englishtutorai.ru/student/cards",
        )

    def _is_allowed_teacher(self, telegram_user_id: int) -> bool:
        return telegram_user_id in self.settings.allowed_teacher_ids

    async def _send_access_denied(self, chat_id: int, telegram_user_id: int) -> None:
        await self.gateway.send_message(
            chat_id,
            ACCESS_DENIED_TEMPLATE.format(telegram_user_id=telegram_user_id),
        )

    async def _ensure_allowed_teacher(self, telegram_user_id: int, chat_id: int) -> bool:
        if self._is_allowed_teacher(telegram_user_id):
            if self.users.get_by_telegram_id(telegram_user_id) is None:
                self.users.get_or_create_teacher(telegram_user_id)
                self.session.commit()
            return True
        await self._send_access_denied(chat_id, telegram_user_id)
        return False

    async def _ensure_allowed_user_or_admin(self, telegram_user_id: int, chat_id: int) -> bool:
        if telegram_user_id == self.settings.telegram_admin_id or self._is_allowed_teacher(telegram_user_id):
            return True
        await self._send_access_denied(chat_id, telegram_user_id)
        return False
