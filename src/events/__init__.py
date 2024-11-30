"""FastStream event handling module."""

# Import all handlers to ensure they're registered
from src.events import (
    attachment_handler,
    crawl_handler,
    schedule_handler,
    telegram_handler,
)
from src.events.broker import app, broker, taskiq_broker
from src.events.event_types import CrawlErrorEvent, EventTopics
from src.events.scheduler import scheduler
from src.events.types import (
    AnnouncementEvent,
    AttachmentEvent,
    CrawlEvent,
    MarkEvent,
    Student,
    TelegramCommandEvent,
    TelegramMessageEvent,
)

# Export public API
__all__ = [
    "broker",
    "app",
    "taskiq_broker",
    "scheduler",
    "crawl_handler",
    "schedule_handler",
    "telegram_handler",
    "attachment_handler",
    "Student",
    "CrawlEvent",
    "CrawlErrorEvent",
    "MarkEvent",
    "AnnouncementEvent",
    "AttachmentEvent",
    "TelegramMessageEvent",
    "TelegramCommandEvent",
    "EventTopics",
]
