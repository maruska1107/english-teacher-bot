from typing import Protocol

import httpx

from app.core.config import Settings


class TelegramNotifierProtocol(Protocol):
    async def send_message(self, chat_id: int, text: str) -> None: ...


class TelegramBotNotifier:
    def __init__(self, settings: Settings) -> None:
        if settings.telegram_bot_token is None:
            raise RuntimeError("Telegram bot token is not configured")
        self.token = settings.telegram_bot_token.get_secret_value()

    async def send_message(self, chat_id: int, text: str) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
            response.raise_for_status()
