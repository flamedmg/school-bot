from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CrawlErrorEvent(BaseModel):
    """Event emitted when a crawling or parsing error occurs"""

    model_config = ConfigDict(validate_default=True, extra="allow")

    timestamp: datetime = Field(
        ..., description="Time when the error occurred", examples=[datetime.now()]
    )
    student_nickname: str = Field(
        ..., description="Student's unique identifier", examples=["student1"]
    )
    error_type: str = Field(
        ...,
        description="Type of error that occurred",
        examples=["login_failed", "parsing_error", "network_error"],
    )
    error_message: str = Field(
        ...,
        description="Detailed error message",
        examples=["Failed to parse schedule: Invalid HTML structure"],
    )
    screenshot_path: str | None = Field(
        None,
        description="Path to error screenshot if available",
        examples=["data/page_failure_20240315_123456.png"],
    )


class EventTopics:
    CRAWL_SCHEDULE = "crawl.schedule"
    CRAWL_ERROR = "crawl.error"  # Topic for crawl errors
    NEW_MARK = "schedule.new_mark"
    NEW_ANNOUNCEMENT = "schedule.new_announcement"
    TELEGRAM_MESSAGE = "telegram.message"
    TELEGRAM_COMMAND = "telegram.command"
    NEW_ATTACHMENT = "schedule.new_attachment"  # Topic for new attachments
