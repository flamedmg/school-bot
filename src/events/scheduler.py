from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fast_depends import Depends, inject
from faststream import FastStream
from faststream.redis import RedisBroker
import logging

from src.config import settings
from src.events.broker import get_broker, get_stream_app

logger = logging.getLogger(__name__)

class EventScheduler:
    @inject
    def __init__(
        self,
        broker: RedisBroker = Depends(get_broker),
        stream_app: FastStream = Depends(get_stream_app)
    ):
        self.broker = broker
        self.stream_app = stream_app
        self.scheduler = AsyncIOScheduler()
        self.crawl_publisher = broker.publisher("crawl.schedule")

    async def emit_crawl_event(self):
        """Emit crawl events for each student to Redis."""
        timestamp = datetime.now().isoformat()
        
        for student in settings.students:
            logger.info(f"Emitting crawl event for student: {student.nickname}")
            await self.crawl_publisher.publish({
                "timestamp": timestamp,
                "student": {
                    "nickname": student.nickname,
                    "email": student.email,
                    "password": student.password,
                    "emoji": student.emoji
                }
            })

    def setup_schedules(self):
        """Set up the complex scheduling requirements."""
        # Weekend schedule - Run once at 10 AM on Saturday and Sunday
        self.scheduler.add_job(
            self.emit_crawl_event,
            CronTrigger(
                day_of_week='sat,sun',
                hour=10,
                minute=0
            ),
            id='weekend_schedule',
            name='Weekend Schedule Check',
            misfire_grace_time=3600  # Allow up to 1 hour delay
        )

        # Weekday schedule - Every 45 minutes from 8 AM to 3 PM
        self.scheduler.add_job(
            self.emit_crawl_event,
            IntervalTrigger(minutes=45),
            id='weekday_schedule',
            name='Weekday Schedule Check',
            day_of_week='mon-fri',
            start_date=datetime.now().replace(
                hour=8, minute=0, second=0, microsecond=0
            ),
            end_date=datetime.now().replace(
                hour=15, minute=0, second=0, microsecond=0
            ),
            misfire_grace_time=900  # Allow up to 15 minutes delay
        )

    async def start(self):
        """Start the scheduler."""
        logger.info("Starting event scheduler")
        self.setup_schedules()
        self.scheduler.start()
        logger.info("Event scheduler started successfully")

    async def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping event scheduler")
        self.scheduler.shutdown()
        logger.info("Event scheduler stopped successfully")
