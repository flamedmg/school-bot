"""FastStream event handling module."""

from src.events.types import (
    Student,
    CrawlEvent,
    MarkEvent,
    AnnouncementEvent,
    TelegramMessageEvent,
    TelegramCommandEvent,
    EventTopics
)
from src.events.base_handler import BaseEventHandler
from src.events.crawl_handler import CrawlEventHandler
from src.events.schedule_handler import ScheduleEventHandler
from src.events.telegram_handler import TelegramEventHandler
from src.events.broker import get_broker, get_stream_app
from src.events.manager import EventManager, event_manager

__all__ = [
    'Student',
    'CrawlEvent',
    'MarkEvent',
    'AnnouncementEvent',
    'TelegramMessageEvent',
    'TelegramCommandEvent',
    'EventTopics',
    'BaseEventHandler',
    'CrawlEventHandler',
    'ScheduleEventHandler',
    'TelegramEventHandler',
    'EventManager',
    'event_manager',
    'get_broker',
    'get_stream_app',
]
