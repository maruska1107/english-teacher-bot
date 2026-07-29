import logging
from collections.abc import Awaitable, Callable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.telegram.commands import TelegramCommandService
from app.telegram.notifier import is_silent_telegram_chat

logger = logging.getLogger(__name__)


class BotGateway:
    def __init__(self, context: ContextTypes.DEFAULT_TYPE, settings: Settings) -> None:
        self.context = context
        self.settings = settings

    async def send_message(self, chat_id: int, text: str) -> None:
        if is_silent_telegram_chat(self.settings, chat_id):
            logger.info("Suppressing Telegram bot response for silent user_id=%s", chat_id)
            return
        await self.context.bot.send_message(chat_id=chat_id, text=text)

    async def send_webapp_button(self, chat_id: int, text: str, button_text: str, webapp_url: str) -> None:
        if is_silent_telegram_chat(self.settings, chat_id):
            logger.info("Suppressing Telegram bot WebApp button for silent user_id=%s", chat_id)
            return
        reply_markup = InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(text=button_text, web_app=WebAppInfo(url=webapp_url))
        )
        await self.context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


def is_telegram_bot_configured(settings: Settings) -> bool:
    token = settings.telegram_bot_token.get_secret_value() if settings.telegram_bot_token else ""
    return bool(token and token != "replace-me")


def build_telegram_application(settings: Settings | None = None) -> Application | None:
    settings = settings or get_settings()
    if not is_telegram_bot_configured(settings):
        return None

    token_secret = settings.telegram_bot_token
    if token_secret is None:
        return None
    token = token_secret.get_secret_value()
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", _start_handler(settings)))
    application.add_handler(CommandHandler("connect_zoom", _command_handler("handle_connect_zoom", settings)))
    application.add_handler(CommandHandler("cards", _command_handler("handle_cards", settings)))
    application.add_handler(
        CommandHandler("add_student", _text_command_handler("handle_add_student", settings, "student_name"))
    )
    application.add_handler(
        CommandHandler("add_group", _text_command_handler("handle_add_group", settings, "group_spec"))
    )
    application.add_handler(
        CommandHandler("add_zoom_meeting", _text_command_handler("handle_add_zoom_meeting", settings, "meeting_link"))
    )
    application.add_handler(CommandHandler("disconnect_zoom", _command_handler("handle_disconnect_zoom", settings)))
    application.add_handler(CommandHandler("status", _command_handler("handle_status", settings)))
    application.add_handler(CommandHandler("last_report", _command_handler("handle_last_report", settings)))
    application.add_handler(CommandHandler("last_error", _command_handler("handle_last_error", settings)))
    application.add_error_handler(_error_handler)
    return application


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Telegram update failed", exc_info=context.error)


def _start_handler(settings: Settings) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.effective_chat is None:
            return

        with SessionLocal() as session:
            service = TelegramCommandService(
                session=session,
                gateway=BotGateway(context, settings),
                settings=settings,
            )
            await service.handle_start(
                telegram_user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                start_payload=" ".join(context.args or []),
            )

    return handler


def _command_handler(
    method_name: str, settings: Settings
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.effective_chat is None:
            return

        with SessionLocal() as session:
            service = TelegramCommandService(
                session=session,
                gateway=BotGateway(context, settings),
                settings=settings,
            )
            method = getattr(service, method_name)
            await method(
                telegram_user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
            )

    return handler


def _text_command_handler(
    method_name: str, settings: Settings, text_parameter_name: str
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.effective_chat is None:
            return

        with SessionLocal() as session:
            service = TelegramCommandService(
                session=session,
                gateway=BotGateway(context, settings),
                settings=settings,
            )
            method = getattr(service, method_name)
            await method(
                telegram_user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                **{text_parameter_name: " ".join(context.args or [])},
            )

    return handler
