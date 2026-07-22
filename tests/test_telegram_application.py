from app.core.config import Settings
from app.telegram.application import is_telegram_bot_configured


def test_telegram_bot_disabled_when_token_missing_or_placeholder():
    assert is_telegram_bot_configured(Settings(telegram_bot_token=None)) is False
    assert is_telegram_bot_configured(Settings(telegram_bot_token="replace-me")) is False


def test_telegram_bot_enabled_when_real_token_is_configured():
    assert is_telegram_bot_configured(Settings(telegram_bot_token="123:abc")) is True
