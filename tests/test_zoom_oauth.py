from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.zoom import get_telegram_notifier, get_zoom_oauth_client
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_app
from app.models import User, ZoomToken
from app.repositories.zoom_oauth_states import ZoomOAuthStateRepository
from app.telegram.messages import ZOOM_CONNECTED_TEXT
from app.zoom.oauth import ZoomOAuthService, ZoomTokenPayload, ZoomUserProfile


class FakeTelegramNotifier:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))


class FakeZoomOAuthClient:
    def __init__(self) -> None:
        self.exchanged_codes: list[str] = []

    async def exchange_code_for_token(self, code: str) -> ZoomTokenPayload:
        self.exchanged_codes.append(code)
        return ZoomTokenPayload(
            access_token="zoom-access-token",
            refresh_token="zoom-refresh-token",
            expires_in=3600,
        )

    async def get_current_user(self, access_token: str) -> ZoomUserProfile:
        assert access_token == "zoom-access-token"
        return ZoomUserProfile(
            zoom_user_id="zoom-user-1",
            zoom_account_id="zoom-account-1",
        )


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory()


def make_settings() -> Settings:
    return Settings(
        app_env="test",
        allowed_telegram_teacher_ids="1001",
        telegram_admin_id=9001,
        zoom_client_id="zoom-client-id",
        zoom_client_secret="zoom-client-secret",
        zoom_redirect_uri="https://bot.example.com/api/zoom/oauth/callback",
        zoom_webhook_secret_token="zoom-webhook-secret",
    )


def test_build_authorization_url_stores_state_for_user():
    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.commit()
    service = ZoomOAuthService(session=session, settings=make_settings())

    url = service.build_authorization_url(teacher)

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert parsed.netloc == "zoom.us"
    assert parsed.path == "/oauth/authorize"
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["zoom-client-id"]
    assert query["redirect_uri"] == ["https://bot.example.com/api/zoom/oauth/callback"]
    assert query["state"]

    stored_state = ZoomOAuthStateRepository(session).get_valid(query["state"][0])
    assert stored_state is not None
    assert stored_state.user_id == teacher.id
    assert stored_state.consumed_at is None


async def test_complete_callback_validates_state_and_upserts_zoom_token():
    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.commit()
    service = ZoomOAuthService(session=session, settings=make_settings())
    state = ZoomOAuthStateRepository(session).create(user_id=teacher.id, ttl_minutes=10)
    session.commit()

    await service.complete_oauth_callback(
        code="zoom-auth-code",
        state_token=state.state,
        client=FakeZoomOAuthClient(),
    )

    token = session.query(ZoomToken).filter_by(user_id=teacher.id).one()
    assert token.zoom_account_id == "zoom-account-1"
    assert token.zoom_user_id == "zoom-user-1"
    assert token.access_token == "zoom-access-token"
    assert token.refresh_token == "zoom-refresh-token"
    assert token.expires_at.replace(tzinfo=UTC) > datetime.now(UTC) + timedelta(minutes=55)
    assert ZoomOAuthStateRepository(session).get_valid(state.state) is None


async def test_complete_callback_rejects_reused_or_unknown_state():
    session = make_session()
    service = ZoomOAuthService(session=session, settings=make_settings())

    try:
        await service.complete_oauth_callback(
            code="zoom-auth-code",
            state_token="unknown-state",
            client=FakeZoomOAuthClient(),
        )
    except ValueError as exc:
        assert str(exc) == "Invalid or expired OAuth state"
    else:
        raise AssertionError("Expected invalid state to raise ValueError")


def test_zoom_callback_endpoint_saves_token_and_returns_success():
    session = make_session()
    teacher = User(telegram_user_id=1001, role="teacher", is_active=True)
    session.add(teacher)
    session.commit()
    state = ZoomOAuthStateRepository(session).create(user_id=teacher.id, ttl_minutes=10)
    session.commit()

    app = create_app()
    app.dependency_overrides[get_settings] = make_settings

    def override_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    fake_client = FakeZoomOAuthClient()
    fake_notifier = FakeTelegramNotifier()
    app.dependency_overrides[get_zoom_oauth_client] = lambda: fake_client
    app.dependency_overrides[get_telegram_notifier] = lambda: fake_notifier
    client = TestClient(app)

    response = client.get(f"/api/zoom/oauth/callback?code=zoom-auth-code&state={state.state}")

    assert response.status_code == 200
    assert response.json() == {"status": "connected"}
    assert fake_client.exchanged_codes == ["zoom-auth-code"]
    assert session.query(ZoomToken).filter_by(user_id=teacher.id).one().zoom_user_id == "zoom-user-1"
    assert fake_notifier.messages == [(1001, ZOOM_CONNECTED_TEXT)]
