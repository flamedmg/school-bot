from datetime import datetime
from loguru import logger
from faststream.redis import RedisBroker

from src.events.types import EventTopics, CrawlEvent, Student
from src.config import settings

async def trigger_initial_crawls(broker: RedisBroker):
    """Trigger initial crawl events for all configured students."""
    logger.info("Triggering initial crawls for all students...")
    
    try:
        for student_config in settings.students:
            logger.info(f"Setting up initial crawl for student: {student_config.nickname}")
            
            # Create Student model
            student = Student(
                nickname=student_config.nickname,
                email=student_config.email,
                password=student_config.password,
                emoji=student_config.emoji
            )
            
            # Create CrawlEvent
            event = CrawlEvent(
                timestamp=datetime.now(),
                student=student
            )
            
            # Trigger initial crawl for this student
            try:
                await broker.publish(event, channel=EventTopics.CRAWL_SCHEDULE)
                logger.info(f"Triggered initial crawl for student: {student.nickname}")
            except Exception as e:
                logger.error(f"Failed to trigger initial crawl for {student.nickname}: {str(e)}")

        logger.info("All initial crawls triggered successfully")
    except Exception as e:
        logger.error(f"Error in trigger_initial_crawls: {str(e)}")
        raise
