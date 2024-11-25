import logging
from telethon import TelegramClient
from faststream import Depends

from src.config import settings
from src.events.types import CrawlEvent, EventTopics
from src.schedule.manager import StudentManager
from src.events.broker import broker, get_telegram, get_repository
from src.database.repository import ScheduleRepository

logger = logging.getLogger(__name__)

@broker.subscriber(EventTopics.CRAWL_SCHEDULE)
async def handle_crawl_event(
    event: CrawlEvent,
    telegram: TelegramClient = Depends(get_telegram),
    repository: ScheduleRepository = Depends(get_repository)
):
    """Handle crawl events for schedule updates."""
    try:
        student = event.student
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
        logger.info(f"Successfully processed schedules for student: {student.nickname}")
        
    except Exception as e:
        logger.error(f"Error processing crawl event: {str(e)}")
        # Send error notification with student's emoji
        await telegram.send_message(
            settings.telegram_chat_id,
            f"{student.emoji} Error processing schedule for {student.nickname}: {str(e)}"
        )
