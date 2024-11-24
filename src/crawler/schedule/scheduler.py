from datetime import datetime, time
import asyncio
from faststream import FastStream
from faststream.redis import RedisBroker
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fast_depends import Depends, inject

from src.config import settings
from src.dependencies import Dependencies

class CrawlScheduler:
    def __init__(self, broker: RedisBroker, stream_app: FastStream):
        self.broker = broker
        self.stream_app = stream_app
        self.scheduler = AsyncIOScheduler()
        
        # Create a publisher for crawl events
        self.crawl_publisher = broker.publisher("crawl.schedule")

    @inject
    async def emit_crawl_event(self):
        """Emit crawl events for each student to Redis"""
        timestamp = datetime.now().isoformat()
        
        # Emit an event for each student
        for student in settings.students:
            await self.crawl_publisher.publish({
                "timestamp": timestamp,
                "student": {
                    "nickname": student.nickname,
                    "email": student.email,
                    "password": student.password
                }
            })

    def setup_schedules(self):
        """Set up the complex scheduling requirements"""
        # Weekend schedule - Run once at 10 AM on Saturday and Sunday
        self.scheduler.add_job(
            self.emit_crawl_event,
            CronTrigger(
                day_of_week='sat,sun',
                hour=10,
                minute=0
            ),
            id='weekend_schedule'
        )

        # Weekday schedule - Every 45 minutes from 8 AM to 3 PM
        self.scheduler.add_job(
            self.emit_crawl_event,
            IntervalTrigger(minutes=45),
            id='weekday_schedule',
            day_of_week='mon-fri',
            start_date=datetime.now().replace(
                hour=8, minute=0, second=0, microsecond=0
            ),
            end_date=datetime.now().replace(
                hour=15, minute=0, second=0, microsecond=0
            )
        )

    async def start(self):
        """Start the scheduler"""
        self.setup_schedules()
        self.scheduler.start()

    async def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
