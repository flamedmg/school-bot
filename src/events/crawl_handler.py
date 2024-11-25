from telethon import TelegramClient
from faststream import Depends, Logger
from loguru import logger as loguru_logger
from datetime import datetime

from src.config import settings
from src.events.types import CrawlEvent, CrawlErrorEvent, EventTopics
from src.schedule.manager import StudentManager
from src.events.broker import broker, get_telegram, get_repository
from src.database.repository import ScheduleRepository

@broker.subscriber(EventTopics.CRAWL_SCHEDULE)
async def handle_crawl_event(
    event: CrawlEvent,
    logger: Logger,
    telegram: TelegramClient = Depends(get_telegram),
    repository: ScheduleRepository = Depends(get_repository)
):
    """Handle crawl events for schedule updates."""
    try:
        student = event.student
        loguru_logger.info(f"Processing crawl event for student: {student.nickname}")
        logger.info(f"Processing crawl event for student: {student.nickname}")
        
        # Create and use StudentManager to process schedules
        manager = StudentManager(
            email=student.email,
            password=student.password,
            nickname=student.nickname,
            broker=broker,
            repository=repository
        )
        
        await manager.process_schedules()
        loguru_logger.info(f"Successfully processed schedules for student: {student.nickname}")
        logger.info(f"Successfully processed schedules for student: {student.nickname}")
        
    except Exception as e:
        error_msg = f"Error processing crawl event: {str(e)}"
        loguru_logger.error(error_msg)
        logger.error(error_msg)
        
        # Emit error event instead of direct telegram message
        error_event = CrawlErrorEvent(
            timestamp=datetime.now(),
            student_nickname=event.student.nickname,
            error_type="crawl_event_error",
            error_message=error_msg
        )
        await broker.publish(error_event, EventTopics.CRAWL_ERROR)
