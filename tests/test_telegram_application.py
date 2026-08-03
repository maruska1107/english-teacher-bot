from app.core.config import Settings
from app.telegram.application import BOT_COMMANDS, BotGateway, is_telegram_bot_configured, register_bot_commands


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []
        self.webapp_messages: list[tuple[int, str, object]] = []
        self.commands = None

    async def send_message(self, chat_id: int, text: str, reply_markup=None) -> None:
        if reply_markup is None:
            self.messages.append((chat_id, text))
        else:
            self.webapp_messages.append((chat_id, text, reply_markup))

    async def set_my_commands(self, commands) -> None:
        self.commands = commands


class FakeApplication:
    def __init__(self) -> None:
        self.bot = FakeBot()


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


async def test_register_bot_commands_sets_telegram_command_menu():
    application = FakeApplication()

    await register_bot_commands(application)

    assert application.bot.commands == BOT_COMMANDS
    command_names = [command.command for command in BOT_COMMANDS]
    assert command_names == [
        "start",
        "connect_zoom",
        "disconnect_zoom",
        "status",
        "cards",
        "add_student",
        "add_group",
        "add_zoom_meeting",
        "last_report",
        "last_error",
        "dev_seed_data",
    ]
    assert all(command.description for command in BOT_COMMANDS)
    assert next(command.description for command in BOT_COMMANDS if command.command == "dev_seed_data") == (
        "Добавить тестовые карточки"
    )


async def test_bot_gateway_sends_webapp_button_with_reply_markup():
    settings = Settings()
    context = FakeContext()
    gateway = BotGateway(context, settings)

    await gateway.send_webapp_button(956230172, "Карточки", "Открыть WebApp", "https://englishtutorai.ru/teacher/cards")

    assert len(context.bot.webapp_messages) == 1
    chat_id, text, reply_markup = context.bot.webapp_messages[0]
    assert chat_id == 956230172
    assert text == "Карточки"
    button = reply_markup.inline_keyboard[0][0]
    assert button.text == "Открыть WebApp"
    assert button.web_app.url == "https://englishtutorai.ru/teacher/cards"


async def test_bot_gateway_suppresses_webapp_button_to_silent_user_ids():
    settings = Settings(silent_telegram_user_ids="925045715")
    context = FakeContext()
    gateway = BotGateway(context, settings)

    await gateway.send_webapp_button(925045715, "не отправлять", "Открыть", "https://englishtutorai.ru/teacher/cards")

    assert context.bot.messages == []
    assert context.bot.webapp_messages == []
