from datetime import datetime
from taskiq_faststream import StreamScheduler
from taskiq.schedule_sources import LabelScheduleSource
from loguru import logger

from src.events.broker import taskiq_broker, broker, app
from src.events.types import CrawlEvent, Student
from src.events.event_types import EventTopics
from src.config import settings

# Create scheduler instance
scheduler = StreamScheduler(
    broker=taskiq_broker,
    sources=[LabelScheduleSource(taskiq_broker)],
)


@app.on_startup
async def setup_schedules():
    """Setup scheduled tasks for each student."""
    logger.info("Setting up scheduled tasks...")

    try:
        for student_config in settings.students:
            logger.info(
                f"Setting up crawl schedule for student: {student_config.nickname}"
            )

            # Create Student model
            student = Student(
                nickname=student_config.nickname,
                username=student_config.username,
                password=student_config.password,
                emoji=student_config.emoji,
            )

            # Create CrawlEvent
            event = CrawlEvent(timestamp=datetime.now(), student=student)

            # Schedule the task using taskiq_broker
            taskiq_broker.task(
                message=event.model_dump(),
                channel=EventTopics.CRAWL_SCHEDULE,
                schedule=[
                    # Weekend schedule - Run once at 10 AM on Saturday and Sunday
                    {
                        "cron": "0 10 * * 6,0",  # At 10:00 on Saturday and Sunday
                        "labels": ["weekend_schedule"],
                    },
                    # Weekday schedule - Every 45 minutes from 8 AM to 3 PM
                    {
                        "cron": "*/45 8-15 * * 1-5",  # Every 45 minutes between 8 AM and 3 PM on weekdays
                        "labels": ["weekday_schedule"],
                    },
                ],
            )
            logger.debug(
                f"Scheduled crawl tasks for {student.nickname}: weekday (*/45 8-15 * * 1-5) and weekend (0 10 * * 6,0)"
            )

        logger.info("All scheduled tasks set up successfully")
    except Exception as e:
        logger.error(f"Error in setup_schedules: {str(e)}")
        raise
