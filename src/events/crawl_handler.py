from telethon import TelegramClient
from faststream import Depends, Logger
from loguru import logger as loguru_logger
from datetime import datetime

from src.config import settings
from src.events.types import CrawlEvent
from src.events.event_types import CrawlErrorEvent, EventTopics
from src.schedule.manager import StudentManager
from src.schedule.exceptions import CrawlException
from src.events.broker import broker, get_telegram, get_repository
from src.database.repository import ScheduleRepository


@broker.subscriber(EventTopics.CRAWL_SCHEDULE)
async def handle_crawl_event(
    event: CrawlEvent,
    logger: Logger,
    telegram: TelegramClient = Depends(get_telegram),
    repository: ScheduleRepository = Depends(get_repository),
):
    """Handle crawl events for schedule updates."""
    try:
        student = event.student
        logger.info(f"Processing crawl event for student: **{student.nickname}**")

        # Create and use StudentManager to process schedules
        manager = StudentManager(
            username=student.username,
            password=student.password,
            nickname=student.nickname,
            broker=broker,
            repository=repository,
        )

        await manager.process_schedules()
        loguru_logger.info(
            f"Successfully processed schedules for student: **{student.nickname}**"
        )

    except CrawlException as e:
        # The manager will have already converted this to an event and published it
        loguru_logger.error(f"Crawl error: {e.error_type} - {e.message}")
        logger.error(f"Crawl error: {e.error_type} - {e.message}")
        raise

    except Exception as e:
        error_msg = f"Error processing crawl event: {str(e)}"
        loguru_logger.error(error_msg)
        logger.error(error_msg)

        # Create and emit error event for unexpected errors
        error_event = CrawlErrorEvent(
            timestamp=datetime.now(),
            student_nickname=event.student.nickname,
            error_type="crawl_event_error",
            error_message=error_msg,
        )
        await broker.publish(error_event, EventTopics.CRAWL_ERROR)
        raise
