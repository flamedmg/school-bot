import logging
from datetime import datetime
from faststream.redis import RedisBroker, RedisMessage
from faststream import FastStream
from telethon import TelegramClient
from sqlalchemy.ext.asyncio import AsyncSession
from faststream.annotations import Logger
from fast_depends import Depends, inject
from contextlib import asynccontextmanager

from src.config import settings
from src.dependencies import Dependencies
from src.database import AsyncSessionLocal
from src.schedule.crawler import crawl_schedules

logger = logging.getLogger(__name__)


class CrawlHandlers:
    def __init__(self, broker: RedisBroker, app: FastStream):
        self.broker = broker
        self.app = app

        # Register handlers
        self.setup_handlers()

        # Register startup handler for initial crawl
        app.after_startup(self.initial_crawl)

    def setup_handlers(self):
        """Set up message handlers"""

        @self.broker.subscriber("crawl.schedule")
        @inject
        async def handle_crawl_event(
            message: RedisMessage,
            logger: Logger,
            bot: TelegramClient = Depends(Dependencies.get_bot),
        ):
            """Handle crawl events with injected dependencies"""
            data = message.data
            timestamp = data["timestamp"]
            student = data.get("student", {})

            async with AsyncSessionLocal() as db:
                if student:
                    logger.info(
                        f"Received crawl event at {timestamp} for student {student['nickname']}"
                    )

                    try:
                        # Crawl schedules for three weeks
                        schedules = await crawl_schedules(
                            email=student["email"], password=student["password"]
                        )

                        if schedules:
                            logger.info(
                                f"Successfully crawled {len(schedules)} schedules for {student['nickname']}"
                            )

                            # Here you would process the schedules and store them in the database
                            # The schedules list contains HTML content for each week
                            # You can parse them using your existing schedule processing logic

                            # Example:
                            # for schedule_html in schedules:
                            #     processed_schedule = process_schedule(schedule_html)
                            #     await db.save_schedule(processed_schedule)

                            await db.commit()

                            # Notify success via Telegram
                            await bot.send_message(
                                settings.admin_chat_id,
                                f"Successfully crawled schedules for {student['nickname']}",
                            )
                        else:
                            error_msg = (
                                f"No schedules retrieved for {student['nickname']}"
                            )
                            logger.error(error_msg)
                            await bot.send_message(
                                settings.admin_chat_id, f"Error: {error_msg}"
                            )

                    except Exception as e:
                        error_msg = f"Error processing schedules for {student['nickname']}: {str(e)}"
                        logger.error(error_msg)
                        await bot.send_message(
                            settings.admin_chat_id, f"Error: {error_msg}"
                        )

                else:
                    logger.warning(
                        f"Received crawl event at {timestamp} without student information"
                    )

    @inject
    async def initial_crawl(self):
        """Execute initial crawl for all students after startup"""
        timestamp = datetime.now().isoformat()
        for student in settings.students:
            await self.broker.publish(
                {
                    "timestamp": timestamp,
                    "student": {
                        "nickname": student.nickname,
                        "email": student.email,
                        "password": student.password,
                    },
                },
                "crawl.schedule",
            )
