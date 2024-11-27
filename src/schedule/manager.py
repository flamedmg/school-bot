from datetime import datetime
from typing import List, Dict
from faststream.redis import RedisBroker
from loguru import logger

from src.schedule.crawler import ScheduleCrawler
from src.schedule.exceptions import CrawlException
from src.database.repository import ScheduleRepository
from src.events.event_types import CrawlErrorEvent, EventTopics


class StudentManager:
    def __init__(
        self,
        username: str,
        password: str,
        nickname: str,
        broker: RedisBroker,
        repository: ScheduleRepository,
    ):
        self.username = username
        self.password = password
        self.nickname = nickname
        self.broker = broker
        self.repository = repository

    async def process_schedules(self):
        """Main process to handle schedule crawling and change detection."""
        logger.info("Starting schedule processing...")

        try:
            # Initialize the crawler
            crawler = ScheduleCrawler(self.username, self.password, self.nickname)

            # Get schedules for the current and surrounding weeks
            schedules = await crawler.get_schedules()

            # Detect changes using the repository
            changes = self.detect_changes(schedules)

            # Emit events if changes are detected
            if changes:
                await self.broker.publish(
                    {"student_nickname": self.nickname, "changes": changes},
                    "schedule.change_detected",
                )

            # Save the schedules to the repository
            self.save_schedules(schedules)

            logger.info("Schedule processing completed.")

        except CrawlException as e:
            # Convert CrawlException to CrawlErrorEvent
            error_event = CrawlErrorEvent(
                timestamp=e.timestamp,
                student_nickname=e.student_nickname or self.nickname,
                error_type=e.error_type,
                error_message=e.message,
                screenshot_path=e.screenshot_path,
            )
            await self.broker.publish(error_event, EventTopics.CRAWL_ERROR)
            logger.error(f"Crawl error: {e.error_type} - {e.message}")
            raise  # Re-raise the exception after publishing the event

        except Exception as e:
            # Handle unexpected errors
            error_event = CrawlErrorEvent(
                timestamp=datetime.now(),
                student_nickname=self.nickname,
                error_type="unexpected_error",
                error_message=str(e),
            )
            await self.broker.publish(error_event, EventTopics.CRAWL_ERROR)
            logger.error(f"Unexpected error: {str(e)}")
            raise

    def detect_changes(self, schedules: List[Dict]) -> Dict:
        """Detect changes in the schedules using the repository."""
        logger.info("Detecting changes in schedules...")
        # Implement change detection logic using the repository
        # This is a placeholder for the actual change detection logic
        return {"marks": [], "subjects": [], "announcements": []}

    def save_schedules(self, schedules: List[Dict]):
        """Save the schedules to the repository."""
        logger.info("Saving schedules to the repository...")
        # Implement logic to save schedules using the repository
        # This is a placeholder for the actual save logic
        pass
