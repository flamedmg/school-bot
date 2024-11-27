from typing import List, Dict
from pydantic import Field, RedisDsn, BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import re


class StudentConfig(BaseModel):
    """Configuration for a single student."""

    nickname: str = Field(description="Nickname to identify the student")
    username: str = Field(description="Student's school username")
    password: str = Field(description="Student's school password")
    emoji: str = Field(
        default="👤", description="Emoji to represent the student in notifications"
    )


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram settings
    telegram_api_id: int = Field(description="Telegram API ID from my.telegram.org")
    telegram_api_hash: str = Field(description="Telegram API hash from my.telegram.org")
    telegram_bot_token: str = Field(description="Telegram Bot token from @BotFather")
    telegram_chat_id: int = Field(description="Telegram Chat ID to send notifications")

    # School settings
    school_website_url: str = Field(description="School website URL")
    school_email_server: str = Field(description="Email server hostname")

    # Database settings
    database_url: str = Field(
        default="sqlite:///data/school_bot.db", description="Database connection string"
    )

    # Redis settings
    redis_url: RedisDsn = Field(
        default="redis://redis:6379/0", description="Redis connection URL"
    )

    # FastAPI settings
    api_host: str = Field(default="0.0.0.0", description="FastAPI server host")
    api_port: int = Field(default=8000, description="FastAPI server port")
    api_workers: int = Field(default=1, description="Number of API workers")

    # Field validators
    @field_validator(
        "telegram_api_id", "telegram_chat_id", "api_port", "api_workers", mode="before"
    )
    def convert_to_int(cls, v):
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
        mode="before",
    )
    def clean_string(cls, v):
        if isinstance(v, str):
            # Remove any comments and whitespace
            return v.split("#")[0].strip()
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # Changed to False to handle uppercase env vars
        validate_default=True,
        extra="allow",  # Allow extra fields for student configs
    )

    @property
    def students(self) -> List[StudentConfig]:
        """Parse student configurations from environment variables"""
        students = []
        student_pattern = re.compile(
            r"^STUDENT_(USERNAME|PASSWORD|EMOJI)_(.+)$", re.IGNORECASE
        )

        # Collect all student-related environment variables
        student_vars: Dict[str, dict] = {}
        env_vars = {
            k: v
            for k, v in self.model_dump().items()
            if isinstance(k, str) and isinstance(v, (str, int))
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
        for nickname, config in student_vars.items():
            if "username" in config and "password" in config:
                # Set default emoji if not provided
                if "emoji" not in config:
                    config["emoji"] = "👤"
                students.append(StudentConfig(**config))

        if not students:
            raise ValueError(
                "At least one student must be configured using STUDENT_USERNAME_<nickname> and STUDENT_PASSWORD_<nickname>"
            )

        return students


settings = Settings()
