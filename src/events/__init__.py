"""FastStream event handling module."""

from src.events.types import (
    Student,
    CrawlEvent,
    MarkEvent,
    AnnouncementEvent,
    AttachmentEvent,
    TelegramMessageEvent,
    TelegramCommandEvent,
)
from src.events.event_types import CrawlErrorEvent, EventTopics
from src.events.broker import broker, app, taskiq_broker
from src.events.scheduler import scheduler

# Import all handlers to ensure they're registered
from src.events import crawl_handler
from src.events import schedule_handler
from src.events import telegram_handler
from src.events import attachment_handler

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
