from functools import lru_cache
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import Field, PostgresDsn, SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "english-teacher-bot"
    app_env: str = "development"
    log_level: str = "INFO"

    database_url_override: PostgresDsn | None = Field(default=None, alias="DATABASE_URL")
    postgres_user: str = "english_teacher"
    postgres_password: SecretStr = SecretStr("english_teacher_password")
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "english_teacher_bot"

    telegram_bot_token: SecretStr | None = None
    telegram_bot_username: str = "EnglishTutorHelperAIBot"
    allowed_telegram_teacher_ids: str = ""
    silent_telegram_user_ids: str = ""
    telegram_admin_id: int | None = None

    zoom_client_id: str | None = None
    zoom_client_secret: SecretStr | None = None
    zoom_redirect_uri: str | None = None
    zoom_webhook_secret_token: SecretStr | None = None
    zoom_oauth_state_ttl_minutes: int = 15
    auto_process_zoom_webhook_lessons: bool = True
    zoom_review_access_enabled: bool = False

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"

    openverse_images_enabled: bool = True
    openverse_api_base_url: str = "https://api.openverse.org/v1"
    openverse_timeout_seconds: float = Field(default=4.0, gt=0, le=30, allow_inf_nan=False)
    openverse_result_page_size: int = Field(default=3, ge=1, le=50)
    openverse_batch_concurrency: int = Field(default=2, ge=1, le=10)
    openverse_user_agent: str = "EnglishTutorAI/0.1 (support@englishtutorai.ru)"

    @field_validator("openverse_api_base_url")
    @classmethod
    def validate_openverse_api_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized or len(normalized) > 2048:
            raise ValueError("Openverse API base URL must be between 1 and 2048 characters")
        try:
            parsed = urlsplit(normalized)
            hostname = parsed.hostname
        except ValueError as exc:
            raise ValueError("Openverse API base URL is invalid") from exc
        if parsed.scheme != "https" or not hostname:
            raise ValueError("Openverse API base URL must be an absolute HTTPS URL with a host")
        return normalized

    @field_validator("openverse_user_agent")
    @classmethod
    def validate_openverse_user_agent(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or len(normalized) > 255:
            raise ValueError("Openverse user agent must be between 1 and 255 characters")
        return normalized

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> PostgresDsn:
        if self.database_url_override is not None:
            return self.database_url_override

        password = self.postgres_password.get_secret_value()
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.postgres_user,
            password=password,
            host=self.postgres_host,
            port=self.postgres_port,
            path=self.postgres_db,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_teacher_ids(self) -> list[int]:
        return self._parse_int_list(self.allowed_telegram_teacher_ids)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def silent_user_ids(self) -> list[int]:
        return self._parse_int_list(self.silent_telegram_user_ids)

    def _parse_int_list(self, raw_value: str) -> list[int]:
        if not raw_value.strip():
            return []
        return [int(raw_id.strip()) for raw_id in raw_value.split(",") if raw_id.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, get_settings]
