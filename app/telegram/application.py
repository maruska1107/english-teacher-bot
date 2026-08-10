import logging
from collections.abc import Awaitable, Callable

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.telegram.commands import TelegramCommandService
from app.telegram.notifier import is_silent_telegram_chat

logger = logging.getLogger(__name__)

BOT_COMMANDS = (
    BotCommand("start", "Начать работу / подключить ученика"),
    BotCommand("connect_zoom", "Подключить Zoom"),
    BotCommand("disconnect_zoom", "Отключить Zoom"),
    BotCommand("status", "Проверить статус бота"),
    BotCommand("cards", "Открыть карточки для проверки"),
    BotCommand("add_student", "Добавить ученика"),
    BotCommand("add_group", "Добавить группу"),
    BotCommand("add_zoom_meeting", "Добавить Zoom-конференцию"),
    BotCommand("last_report", "Показать последний отчёт"),
    BotCommand("last_error", "Показать последнюю ошибку"),
    BotCommand("dev_seed_data", "Добавить тестовые карточки"),
)


async def register_bot_commands(application: Application) -> None:
    await application.bot.set_my_commands(BOT_COMMANDS)


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

    async def send_inline_buttons(self, chat_id: int, text: str, buttons: list[tuple[str, str]]) -> None:
        if is_silent_telegram_chat(self.settings, chat_id):
            logger.info("Suppressing Telegram bot inline buttons for silent user_id=%s", chat_id)
            return
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text=label, callback_data=callback_data) for label, callback_data in buttons]]
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
    application = Application.builder().token(token).post_init(register_bot_commands).build()
    application.add_handler(CommandHandler("start", _start_handler(settings)))
    application.add_handler(
        CommandHandler("connect", _text_command_handler("handle_connect_alias", settings, "command_args"))
    )
    application.add_handler(CommandHandler("connect_zoom", _command_handler("handle_connect_zoom", settings)))
    application.add_handler(CommandHandler("cards", _command_handler("handle_cards", settings)))
    application.add_handler(
        CommandHandler("add_student", _text_command_handler("handle_add_student", settings, "student_name"))
    )
    application.add_handler(CommandHandler("add_group", _add_group_handler(settings)))
    application.add_handler(CallbackQueryHandler(_group_creation_callback_handler(settings), pattern="^group_create_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _group_creation_text_handler(settings)))
    application.add_handler(
        CommandHandler("add_zoom_meeting", _text_command_handler("handle_add_zoom_meeting", settings, "meeting_link"))
    )
    application.add_handler(CommandHandler("disconnect_zoom", _command_handler("handle_disconnect_zoom", settings)))
    application.add_handler(CommandHandler("status", _command_handler("handle_status", settings)))
    application.add_handler(CommandHandler("last_report", _command_handler("handle_last_report", settings)))
    application.add_handler(CommandHandler("last_error", _command_handler("handle_last_error", settings)))
    application.add_handler(CommandHandler("dev_seed_data", _command_handler("handle_dev_seed_data", settings)))
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


def _add_group_handler(settings: Settings) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.effective_chat is None:
            return
        group_spec = " ".join(context.args or [])
        with SessionLocal() as session:
            service = TelegramCommandService(session=session, gateway=BotGateway(context, settings), settings=settings)
            await service.handle_add_group(
                telegram_user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                group_spec=group_spec,
            )
        if ":" not in group_spec:
            context.user_data["group_creation"] = {"step": "name"}

    return handler


def _group_creation_text_handler(settings: Settings) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        state = context.user_data.get("group_creation")
        if not state or update.effective_user is None or update.effective_chat is None or update.message is None:
            return
        text = update.message.text or ""
        with SessionLocal() as session:
            service = TelegramCommandService(session=session, gateway=BotGateway(context, settings), settings=settings)
            if state.get("step") == "name":
                group_name = text.strip()
                if not group_name:
                    await service.prompt_group_name(update.effective_chat.id)
                    return
                state["group_name"] = group_name
                state["step"] = "members"
                await service.prompt_group_members(chat_id=update.effective_chat.id, group_name=group_name)
                return
            if state.get("step") == "members":
                member_names = await service.handle_group_members_preview(
                    chat_id=update.effective_chat.id,
                    group_name=str(state.get("group_name", "")),
                    raw_member_names=text,
                )
                if member_names is not None:
                    state["member_names"] = member_names
                    state["step"] = "confirm"

    return handler


def _group_creation_callback_handler(
    settings: Settings,
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None or update.effective_user is None or query.message is None:
            return
        await query.answer()
        chat_id = query.message.chat_id
        state = context.user_data.get("group_creation") or {}
        with SessionLocal() as session:
            service = TelegramCommandService(session=session, gateway=BotGateway(context, settings), settings=settings)
            if query.data == "group_create_change":
                context.user_data["group_creation"] = {"step": "name"}
                await service.prompt_group_name(chat_id)
                return
            if query.data == "group_create_confirm":
                group_name = str(state.get("group_name", "")).strip()
                member_names = state.get("member_names")
                if not group_name or not isinstance(member_names, list):
                    context.user_data["group_creation"] = {"step": "name"}
                    await service.prompt_group_name(chat_id)
                    return
                await service.confirm_group_creation(
                    telegram_user_id=update.effective_user.id,
                    chat_id=chat_id,
                    group_name=group_name,
                    member_names=[str(name) for name in member_names],
                )
                context.user_data.pop("group_creation", None)

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
