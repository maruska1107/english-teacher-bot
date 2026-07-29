from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.models import (
    LearningProfile,
    Lesson,
    LessonAnalysis,
    Student,
    User,
    VocabularyCard,
    ZoomMeetingSubscription,
    ZoomToken,
)
from app.telegram.commands import TelegramCommandService
from app.telegram.invites import hash_invite_token
from app.telegram.messages import START_NOTICE_TEXT


class FakeTelegramGateway:
    def __init__(self) -> None:
        self.sent_messages: list[tuple[int, str]] = []
        self.webapp_buttons: list[tuple[int, str, str, str]] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.sent_messages.append((chat_id, text))

    async def send_webapp_button(self, chat_id: int, text: str, button_text: str, webapp_url: str) -> None:
        self.webapp_buttons.append((chat_id, text, button_text, webapp_url))


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory()


def make_settings(**overrides) -> Settings:
    defaults = {
        "app_env": "test",
        "allowed_telegram_teacher_ids": "1001,1002",
        "telegram_admin_id": 9001,
        "zoom_client_id": "zoom-client-id",
        "zoom_client_secret": "zoom-client-secret",
        "zoom_redirect_uri": "https://bot.example.com/api/zoom/oauth/callback",
        "telegram_bot_username": "EnglishTutorHelperAIBot",
    }
    defaults.update(overrides)
    return Settings(**defaults)


async def test_start_creates_allowed_teacher_and_includes_ai_notice():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())

    await service.handle_start(telegram_user_id=1001, chat_id=555)

    user = session.query(User).filter_by(telegram_user_id=1001).one()
    assert user.role == "teacher"
    assert user.is_active is True
    assert gateway.sent_messages == [(555, START_NOTICE_TEXT)]
    assert "уведомить учеников" in gateway.sent_messages[0][1]
    assert "искусственного интеллекта" in gateway.sent_messages[0][1]
    assert "данные" in gateway.sent_messages[0][1].lower()
    assert "транскрипт" not in gateway.sent_messages[0][1].lower()
    assert "видео-записи" in gateway.sent_messages[0][1].lower()
    assert "не хранит" in gateway.sent_messages[0][1].lower()
    assert "удаляет" in gateway.sent_messages[0][1].lower()
    assert "/connect_zoom" in gateway.sent_messages[0][1]


async def test_start_with_student_invite_links_student_telegram_account():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    student = Student(
        teacher_user_id=teacher.id,
        name="Анна",
        invite_token_hash=hash_invite_token("invite-token"),
        invite_status="active",
    )
    session.add(student)
    session.commit()

    await service.handle_start(
        telegram_user_id=222333444,
        chat_id=222333444,
        start_payload="student_invite-token",
    )

    session.refresh(student)
    assert student.telegram_user_id == 222333444
    assert student.invite_status == "used"
    assert gateway.sent_messages == []
    assert gateway.webapp_buttons == [
        (
            222333444,
            (
                "Готово ✅\n"
                "Вы подключены как ученик: Анна.\n\n"
                "Нажмите кнопку ниже, чтобы открыть карточки после уроков."
            ),
            "Открыть карточки",
            "https://englishtutorai.ru/student/cards",
        )
    ]


async def test_start_for_linked_student_returns_cards_webapp_button():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    session.add(
        Student(
            teacher_user_id=teacher.id,
            name="Анна",
            telegram_user_id=222333444,
            invite_status="used",
        )
    )
    session.commit()

    await service.handle_start(telegram_user_id=222333444, chat_id=222333444)

    assert gateway.sent_messages == []
    assert gateway.webapp_buttons == [
        (
            222333444,
            (
                "Готово ✅\n"
                "Вы подключены как ученик: Анна.\n\n"
                "Нажмите кнопку ниже, чтобы открыть карточки после уроков."
            ),
            "Открыть карточки",
            "https://englishtutorai.ru/student/cards",
        )
    ]


async def test_start_with_invalid_student_invite_returns_error_without_linking():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())

    await service.handle_start(telegram_user_id=222333444, chat_id=222333444, start_payload="student_missing")

    assert gateway.sent_messages == [
        (
            222333444,
            "Ссылка недействительна или устарела. Попросите преподавателя отправить новую ссылку.",
        )
    ]


async def test_start_rejects_non_allowed_teacher_without_creating_user():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())

    await service.handle_start(telegram_user_id=7777, chat_id=777)

    assert session.query(User).count() == 0
    assert gateway.sent_messages == [
        (
            777,
            "У вас нет доступа к этому боту.\n\n"
            "Ваш Telegram ID: 7777\n"
            "Передайте этот ID администратору для подключения.",
        )
    ]


async def test_dev_seed_data_admin_command_recreates_test_profile_lessons_and_cards():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(
        session=session,
        gateway=gateway,
        settings=make_settings(telegram_admin_id=956230172),
    )

    await service.handle_dev_seed_data(telegram_user_id=956230172, chat_id=956230172)
    await service.handle_dev_seed_data(telegram_user_id=956230172, chat_id=956230172)

    teacher = session.query(User).filter_by(telegram_user_id=956230172).one()
    student = session.query(Student).filter_by(telegram_user_id=956230172, teacher_user_id=teacher.id).one()
    profile = session.query(LearningProfile).filter_by(teacher_user_id=teacher.id, name="Тест Мария").one()
    lessons = session.query(Lesson).filter_by(teacher_user_id=teacher.id, learning_profile_id=profile.id).all()
    cards = session.query(VocabularyCard).filter_by(teacher_user_id=teacher.id, learning_profile_id=profile.id).all()

    assert student.name == "Тест Мария"
    assert student.invite_status == "used"
    assert len(profile.memberships) == 1
    assert len(lessons) == 2
    assert session.query(LessonAnalysis).join(Lesson).filter(Lesson.learning_profile_id == profile.id).count() == 2
    assert sorted(card.status for card in cards) == ["draft", "draft", "published", "published"]
    assert gateway.sent_messages[-1] == (
        956230172,
        "Тестовые данные готовы ✅\n\n"
        "Профиль: Тест Мария\n"
        "Уроков: 2\n"
        "Draft-карточек: 2\n"
        "Published-карточек: 2\n\n"
        "Откройте /cards для преподавательского WebApp или /start для ученического WebApp.",
    )


async def test_dev_seed_data_is_admin_only():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(
        session=session,
        gateway=gateway,
        settings=make_settings(telegram_admin_id=956230172),
    )

    await service.handle_dev_seed_data(telegram_user_id=1001, chat_id=555)

    assert session.query(LearningProfile).count() == 0
    assert gateway.sent_messages == [(555, "Эта команда доступна только администратору.")]


async def test_status_reports_zoom_connection_and_lesson_count():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    session.add(
        Lesson(
            teacher_user_id=teacher.id,
            meeting_id="1",
            meeting_uuid="uuid-1",
            processing_status="completed",
        )
    )
    session.commit()

    await service.handle_status(telegram_user_id=1001, chat_id=555)

    assert gateway.sent_messages == [
        (
            555,
            "Статус бота\n" "Пользователь: активен\n" "Zoom: не подключён\n" "Обработано уроков: 1",
        )
    ]


async def test_last_report_returns_latest_teacher_analysis():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    first_lesson = Lesson(
        teacher_user_id=teacher.id,
        meeting_id="1",
        meeting_uuid="uuid-1",
        processing_status="completed",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    second_lesson = Lesson(
        teacher_user_id=teacher.id,
        meeting_id="2",
        meeting_uuid="uuid-2",
        processing_status="completed",
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    session.add_all([first_lesson, second_lesson])
    session.flush()
    session.add_all(
        [
            LessonAnalysis(
                lesson_id=first_lesson.id,
                analysis_json={"summary": "old"},
                teacher_report="Old report",
                student_message="Old student message",
                model="gpt-4.1-mini",
                prompt_version="v1",
            ),
            LessonAnalysis(
                lesson_id=second_lesson.id,
                analysis_json={"summary": "new"},
                teacher_report="New report",
                student_message="New student message",
                model="gpt-4.1-mini",
                prompt_version="v1",
            ),
        ]
    )
    session.commit()

    await service.handle_last_report(telegram_user_id=1001, chat_id=555)

    assert gateway.sent_messages == [
        (
            555,
            "Последний отчёт\n\n" "New report\n\n" "Сообщение для учеников\n" "New student message",
        )
    ]


async def test_admin_last_report_returns_latest_analysis_across_teachers():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    lesson = Lesson(
        teacher_user_id=teacher.id,
        meeting_id="3",
        meeting_uuid="uuid-3",
        processing_status="completed",
    )
    session.add(lesson)
    session.flush()
    session.add(
        LessonAnalysis(
            lesson_id=lesson.id,
            analysis_json={"summary": "admin"},
            teacher_report="Admin visible report",
            student_message="Admin visible student message",
            model="gpt-4.1-mini",
            prompt_version="v1",
        )
    )
    session.commit()

    await service.handle_last_report(telegram_user_id=9001, chat_id=9001)

    assert gateway.sent_messages == [
        (
            9001,
            "Последний отчёт\n\n" "Admin visible report\n\n" "Сообщение для учеников\n" "Admin visible student message",
        )
    ]


async def test_admin_last_error_returns_latest_processing_error():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    session.add(
        Lesson(
            teacher_user_id=teacher.id,
            meeting_id="2",
            meeting_uuid="uuid-2",
            processing_status="failed",
            processing_error="Zoom transcript download failed",
        )
    )
    session.commit()

    await service.handle_last_error(telegram_user_id=9001, chat_id=9001)

    assert gateway.sent_messages == [(9001, "Последняя ошибка\nZoom transcript download failed")]


async def test_add_student_creates_individual_profile_and_invite_link():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())

    await service.handle_add_student(telegram_user_id=1001, chat_id=555, student_name="Анна")

    student = session.query(Student).filter_by(name="Анна").one()
    profile = session.query(LearningProfile).filter_by(name="Анна").one()
    assert profile.profile_type == "individual"
    assert profile.memberships[0].student_id == student.id
    assert student.invite_token_hash is not None
    assert "Ссылка для ученика Анна:" in gateway.sent_messages[0][1]
    assert "https://t.me/EnglishTutorHelperAIBot?start=student_" in gateway.sent_messages[0][1]
    assert student.invite_token_hash not in gateway.sent_messages[0][1]


async def test_add_group_creates_group_profile_members_and_invite_links():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())

    await service.handle_add_group(
        telegram_user_id=1001,
        chat_id=555,
        group_spec="Speaking B1: Мария, Катя, Мария",
    )

    profile = session.query(LearningProfile).filter_by(name="Speaking B1").one()
    assert profile.profile_type == "group"
    assert sorted(member.student.name for member in profile.memberships) == ["Катя", "Мария"]
    message = gateway.sent_messages[0][1]
    assert "Группа создана ✅" in message
    assert "Speaking B1" in message
    assert "Мария: https://t.me/EnglishTutorHelperAIBot?start=student_" in message
    assert "Катя: https://t.me/EnglishTutorHelperAIBot?start=student_" in message


async def test_add_group_returns_help_for_invalid_format():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())

    await service.handle_add_group(telegram_user_id=1001, chat_id=555, group_spec="Speaking B1")

    assert gateway.sent_messages == [
        (
            555,
            "Пришлите группу в формате:\n/add_group Название группы: Анна, Мария",
        )
    ]


async def test_cards_command_returns_teacher_webapp_button():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())

    await service.handle_cards(telegram_user_id=1001, chat_id=555)

    assert gateway.sent_messages == []
    assert gateway.webapp_buttons == [
        (
            555,
            "Карточки для проверки:\n"
            "https://englishtutorai.ru/teacher/cards\n\n"
            "Откройте ссылку внутри Telegram, чтобы проверить draft-карточки.",
            "Открыть WebApp",
            "https://englishtutorai.ru/teacher/cards",
        )
    ]


async def test_connect_zoom_returns_oauth_authorization_url():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())

    await service.handle_connect_zoom(telegram_user_id=1001, chat_id=555)

    assert len(gateway.sent_messages) == 1
    chat_id, message = gateway.sent_messages[0]
    assert chat_id == 555
    assert message.startswith("Подключите Zoom по ссылке:\nhttps://zoom.us/oauth/authorize?")
    assert "client_id=zoom-client-id" in message
    assert "state=" in message


async def test_disconnect_zoom_removes_teacher_zoom_tokens():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.flush()
    session.add(
        ZoomToken(
            user_id=teacher.id,
            zoom_account_id="zoom-account-1",
            zoom_user_id="zoom-user-1",
            access_token="access",
            refresh_token="refresh",
            expires_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    session.commit()

    await service.handle_disconnect_zoom(telegram_user_id=1001, chat_id=555)

    assert session.query(ZoomToken).filter_by(user_id=teacher.id).count() == 0
    assert gateway.sent_messages == [(555, "Zoom отключён.")]


async def test_add_zoom_meeting_subscribes_teacher_to_meeting_link():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())

    await service.handle_add_zoom_meeting(
        telegram_user_id=1001,
        chat_id=555,
        meeting_link="https://us06web.zoom.us/j/987654321?pwd=secret",
    )

    user = session.query(User).filter_by(telegram_user_id=1001).one()
    subscription = session.query(ZoomMeetingSubscription).filter_by(user_id=user.id).one()
    assert subscription.meeting_id == "987654321"
    assert subscription.meeting_url == "https://us06web.zoom.us/j/987654321?pwd=secret"
    assert subscription.learning_profile_id is None
    assert subscription.is_active is True
    assert gateway.sent_messages == [
        (
            555,
            "Готово ✅\n"
            "Я буду анализировать данные только по Zoom-конференции 987654321.\n\n"
            "Важно: данные появятся только если подключённый Zoom-аккаунт имеет доступ "
            "к данным этой конференции. Обычно для этого нужен платный Zoom-тариф с "
            "облачной записью и автоматической расшифровкой.",
        )
    ]
    assert "хост" not in gateway.sent_messages[0][1].lower()


async def test_add_zoom_meeting_can_link_to_learning_profile_by_name():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())
    await service.handle_add_group(
        telegram_user_id=1001,
        chat_id=555,
        group_spec="Speaking B1: Мария, Катя",
    )
    gateway.sent_messages.clear()

    await service.handle_add_zoom_meeting(
        telegram_user_id=1001,
        chat_id=555,
        meeting_link="https://us06web.zoom.us/j/777888999 | Speaking B1",
    )

    user = session.query(User).filter_by(telegram_user_id=1001).one()
    profile = session.query(LearningProfile).filter_by(teacher_user_id=user.id, name="Speaking B1").one()
    subscription = session.query(ZoomMeetingSubscription).filter_by(user_id=user.id, meeting_id="777888999").one()
    assert subscription.learning_profile_id == profile.id
    assert subscription.meeting_url == "https://us06web.zoom.us/j/777888999"
    assert "Профиль: Speaking B1" in gateway.sent_messages[0][1]


async def test_add_zoom_meeting_returns_help_for_unknown_learning_profile():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())

    await service.handle_add_zoom_meeting(
        telegram_user_id=1001,
        chat_id=555,
        meeting_link="https://us06web.zoom.us/j/777888999 | Missing Profile",
    )

    assert session.query(ZoomMeetingSubscription).count() == 0
    assert gateway.sent_messages == [(555, "Учебный профиль не найден: Missing Profile")]


async def test_add_zoom_meeting_rejects_invalid_link():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())

    await service.handle_add_zoom_meeting(telegram_user_id=1001, chat_id=555, meeting_link="not-a-zoom-link")

    assert session.query(ZoomMeetingSubscription).count() == 0
    assert "Пришлите ссылку Zoom" in gateway.sent_messages[0][1]
