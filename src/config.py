import re

from pydantic import (
    BaseModel,
    HttpUrl,
    PositiveInt,
    RedisDsn,
    constr,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class StudentConfig(BaseModel):
    """Configuration for a single student."""

    nickname: constr(min_length=1)
    username: constr(min_length=1)
    password: constr(min_length=1)
    emoji: constr(min_length=1, max_length=2) = "👤"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_default=True,
        extra="allow",
    )

    # Telegram settings
    telegram_api_id: PositiveInt
    telegram_api_hash: constr(min_length=1)
    telegram_bot_token: constr(min_length=1)
    telegram_chat_id: int

    # School settings
    school_website_url: HttpUrl
    school_email_server: constr(min_length=1)
    base_url: HttpUrl = "https://www.e-klase.lv"
    schedule_url: HttpUrl = "https://my.e-klase.lv/Family/Diary"

    # Database settings
    database_url: constr(min_length=1) = "sqlite:///data/school_bot.db"

    # Redis settings
    redis_url: RedisDsn = "redis://redis:6379/0"

    # FastAPI settings
    api_host: constr(min_length=1) = "0.0.0.0"
    api_port: PositiveInt = 8000
    api_workers: PositiveInt = 1

    # Crawling settings
    enable_initial_crawl: bool = True  # Disabled by default

    # Field validators
    @field_validator(
        "telegram_api_id", "telegram_chat_id", "api_port", "api_workers", mode="before"
    )
    def convert_to_int(cls, v):  # noqa: N805
        if isinstance(v, str):
            # Remove any comments and whitespace
            v = v.split("#")[0].strip()
            return int(v)
        return v

    @field_validator(
        "telegram_api_hash",
        "telegram_bot_token",
        "school_website_url",
        "school_email_server",
        "base_url",
        "schedule_url",
        mode="before",
    )
    def clean_string(cls, v):  # noqa: N805
        if isinstance(v, str):
            # Remove any comments and whitespace
            return v.split("#")[0].strip()
        return v

    @field_validator("enable_initial_crawl", mode="before")
    def parse_bool(cls, v):  # noqa: N805
        if isinstance(v, str):
            v = v.lower().strip()
            return v in ("1", "true", "yes", "on")
        return bool(v)

    @property
    def students(self) -> list[StudentConfig]:
        """Parse student configurations from environment variables"""
        students = []
        student_pattern = re.compile(
            r"^STUDENT_(USERNAME|PASSWORD|EMOJI)_(.+)$", re.IGNORECASE
        )

        # Collect all student-related environment variables
        student_vars: dict[str, dict] = {}
        env_vars = {
            k: v
            for k, v in self.model_dump().items()
            if isinstance(k, str) and isinstance(v, str | int)
        }

        for key, value in env_vars.items():
            match = student_pattern.match(key)
            if match and isinstance(value, str):
                field, nickname = match.groups()
                # Clean the value (remove comments and whitespace)
                clean_value = value.split("#")[0].strip()
                if nickname not in student_vars:
                    student_vars[nickname] = {"nickname": nickname}
                student_vars[nickname][field.lower()] = clean_value

        # Create StudentConfig objects for complete configurations
        for _nickname, config in student_vars.items():
            if "username" in config and "password" in config:
                # Set default emoji if not provided
                if "emoji" not in config:
                    config["emoji"] = "👤"
                students.append(StudentConfig(**config))

        if not students:
            raise ValueError(
                "At least one student must be configured using "
                "STUDENT_USERNAME_<nickname> and "
                "STUDENT_PASSWORD_<nickname>"
            )

        return students


settings = Settings()
