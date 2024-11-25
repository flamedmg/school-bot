from datetime import datetime, timedelta
from typing import List, Dict
from faststream.redis import RedisBroker
from loguru import logger

from src.schedule.crawler import ScheduleCrawler
from src.database.repository import ScheduleRepository


class StudentManager:
    def __init__(self, email: str, password: str, nickname: str, broker: RedisBroker, repository: ScheduleRepository):
        self.email = email
        self.password = password
        self.nickname = nickname
        self.broker = broker
        self.repository = repository

    async def process_schedules(self):
        """Main process to handle schedule crawling and change detection."""
        logger.info("Starting schedule processing...")
        
        # Initialize the crawler
        crawler = ScheduleCrawler(self.email, self.password, self.nickname)
        
        # Get schedules for the current and surrounding weeks
        schedules = await crawler.get_schedules()
        
        # Detect changes using the repository
        changes = self.detect_changes(schedules)
        
        # Emit events if changes are detected
        if changes:
            await self.broker.publish(
                {"student_nickname": self.nickname, "changes": changes},
                "schedule.change_detected"
            )
        
        # Save the schedules to the repository
        self.save_schedules(schedules)
        
        logger.info("Schedule processing completed.")

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
