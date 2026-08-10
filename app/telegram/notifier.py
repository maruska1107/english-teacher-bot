from typing import Protocol

import httpx

from app.core.config import Settings


def is_silent_telegram_chat(settings: Settings, chat_id: int) -> bool:
    return chat_id in settings.silent_user_ids


class TelegramNotifierProtocol(Protocol):
    async def send_message(self, chat_id: int, text: str) -> None: ...

    async def send_webapp_button(self, chat_id: int, text: str, button_text: str, webapp_url: str) -> None: ...


class TelegramBotNotifier:
    def __init__(self, settings: Settings) -> None:
        if settings.telegram_bot_token is None:
            raise RuntimeError("Telegram bot token is not configured")
        self.settings = settings
        self.token = settings.telegram_bot_token.get_secret_value()

    async def send_message(self, chat_id: int, text: str) -> None:
        if is_silent_telegram_chat(self.settings, chat_id):
            return
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
            response.raise_for_status()

    async def send_webapp_button(self, chat_id: int, text: str, button_text: str, webapp_url: str) -> None:
        if is_silent_telegram_chat(self.settings, chat_id):
            return
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "reply_markup": {
                        "inline_keyboard": [[{"text": button_text, "web_app": {"url": webapp_url}}]],
                    },
                },
            )
            response.raise_for_status()
