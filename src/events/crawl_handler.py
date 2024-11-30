from datetime import datetime

from faststream import Depends, Logger
from loguru import logger as loguru_logger
from telethon import TelegramClient

from src.database.repository import ScheduleRepository
from src.events.broker import broker, get_repository, get_telegram
from src.events.event_types import CrawlErrorEvent, EventTopics
from src.events.types import CrawlEvent
from src.schedule.exceptions import CrawlError
from src.schedule.manager import StudentManager

# Create module-level singletons
telegram_client = Depends(get_telegram)
repository_singleton = Depends(get_repository)


@broker.subscriber(EventTopics.CRAWL_SCHEDULE)
async def handle_crawl_event(
    event: CrawlEvent,
    logger: Logger,
    telegram: TelegramClient = telegram_client,
    repository: ScheduleRepository = repository_singleton,
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

    except CrawlError as e:
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
