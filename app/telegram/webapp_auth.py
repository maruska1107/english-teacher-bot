import hashlib
import hmac
import json
from dataclasses import dataclass
from urllib.parse import parse_qsl

from pydantic import BaseModel, ValidationError

from app.core.config import Settings


class TelegramWebAppUser(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


@dataclass(frozen=True)
class VerifiedTelegramWebAppInitData:
    user: TelegramWebAppUser
    auth_date: str


class TelegramWebAppAuthError(ValueError):
    pass


def verify_telegram_webapp_init_data(init_data: str, settings: Settings) -> VerifiedTelegramWebAppInitData:
    if settings.telegram_bot_token is None:
        raise TelegramWebAppAuthError("Telegram bot token is not configured")
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", None)
    if not received_hash:
        raise TelegramWebAppAuthError("Telegram WebApp hash is missing")
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(
        b"WebAppData",
        settings.telegram_bot_token.get_secret_value().encode(),
        hashlib.sha256,
    ).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise TelegramWebAppAuthError("Telegram WebApp hash is invalid")
    user_json = values.get("user")
    if not user_json:
        raise TelegramWebAppAuthError("Telegram WebApp user is missing")
    try:
        user = TelegramWebAppUser.model_validate(json.loads(user_json))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise TelegramWebAppAuthError("Telegram WebApp user is invalid") from exc
    return VerifiedTelegramWebAppInitData(user=user, auth_date=values.get("auth_date", ""))
