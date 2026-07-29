from app.core.config import Settings
from app.telegram.application import BotGateway, is_telegram_bot_configured


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))


class FakeContext:
    def __init__(self) -> None:
        self.bot = FakeBot()


def test_telegram_bot_disabled_when_token_missing_or_placeholder():
    assert is_telegram_bot_configured(Settings(telegram_bot_token=None)) is False
    assert is_telegram_bot_configured(Settings(telegram_bot_token="replace-me")) is False


def test_telegram_bot_enabled_when_real_token_is_configured():
    assert is_telegram_bot_configured(Settings(telegram_bot_token="123:abc")) is True


def test_silent_telegram_user_ids_are_parsed_from_settings():
    settings = Settings(silent_telegram_user_ids="925045715, 123")

    assert settings.silent_user_ids == [925045715, 123]


async def test_bot_gateway_suppresses_messages_to_silent_user_ids():
    settings = Settings(silent_telegram_user_ids="925045715")
    context = FakeContext()
    gateway = BotGateway(context, settings)

    await gateway.send_message(925045715, "не отправлять")
    await gateway.send_message(956230172, "отправить")

    assert context.bot.messages == [(956230172, "отправить")]
