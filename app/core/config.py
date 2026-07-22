from functools import lru_cache
from typing import Annotated

from pydantic import Field, PostgresDsn, SecretStr, computed_field
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
    allowed_telegram_teacher_ids: str = ""
    telegram_admin_id: int | None = None

    zoom_client_id: str | None = None
    zoom_client_secret: SecretStr | None = None
    zoom_redirect_uri: str | None = None
    zoom_webhook_secret_token: SecretStr | None = None

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"

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
        if not self.allowed_telegram_teacher_ids.strip():
            return []
        return [int(raw_id.strip()) for raw_id in self.allowed_telegram_teacher_ids.split(",") if raw_id.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, get_settings]
