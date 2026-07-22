from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.models import Lesson, LessonAnalysis, User
from app.telegram.commands import TelegramCommandService
from app.telegram.messages import START_NOTICE_TEXT


class FakeTelegramGateway:
    def __init__(self) -> None:
        self.sent_messages: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.sent_messages.append((chat_id, text))


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
    assert "/connect_zoom" in gateway.sent_messages[0][1]


async def test_start_rejects_non_allowed_teacher_without_creating_user():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())

    await service.handle_start(telegram_user_id=7777, chat_id=777)

    assert session.query(User).count() == 0
    assert gateway.sent_messages == [(777, "У вас нет доступа к этому боту. Обратитесь к администратору.")]


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


async def test_connect_zoom_returns_oauth_placeholder_until_zoom_stage():
    session = make_session()
    gateway = FakeTelegramGateway()
    service = TelegramCommandService(session=session, gateway=gateway, settings=make_settings())

    await service.handle_connect_zoom(telegram_user_id=1001, chat_id=555)

    assert gateway.sent_messages == [(555, "Подключение Zoom будет доступно на следующем этапе реализации OAuth.")]
