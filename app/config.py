"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All settings with defaults. Override via .env or environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/voice_transcription"

    # Soniox
    soniox_api_key: str = ""
    soniox_webhook_base: str = "http://localhost:8000"

    # Limits
    transcription_limit: int = 5
    limit_exempt_emails: str = ""  # Comma-separated emails

    # Email (optional)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notification_email: str = ""

    # General
    tz: str = "Europe/Moscow"
    log_level: str = "info"

    @property
    def exempt_emails_list(self) -> list[str]:
        return [e.strip().lower() for e in self.limit_exempt_emails.split(",") if e.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
