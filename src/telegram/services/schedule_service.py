"""Service for handling schedule data retrieval and formatting."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import traceback

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models import Schedule, SchoolDay, Lesson
from src.database.repository import ScheduleRepository


class ScheduleService:
    """Service for handling schedule operations."""

    # Actual lesson times from the schedule
    LESSON_TIMES = {
        1: "8:00-8:40",
        2: "8:50-9:30",
        3: "9:40-10:20",
        4: "10:30-11:10",
        5: "11:30-12:10",
        6: "12:35-13:15",
        7: "13:35-14:15",
        8: "14:25-15:05",
        9: "15:15-15:55",
        10: "16:05-16:45",
    }

    def __init__(self, session: AsyncSession):
        """Initialize the service.

        Args:
            session: The database session
        """
        self.session = session
        self.repository = ScheduleRepository(session)

    def _get_lesson_time(self, index: int) -> str:
        """Convert lesson index to time string.

        Args:
            index: Lesson index (1-based)

        Returns:
            Time string in HH:MM-HH:MM format
        """
        return self.LESSON_TIMES.get(index, "00:00-00:00")

    def _get_week_dates(self, is_next_week: bool = False) -> datetime:
        """Get the appropriate date for schedule based on current time.

        Args:
            is_next_week: Whether to get next week's date

        Returns:
            Target date for schedule
        """
        try:
            now = datetime.now()
            current_week = now.isocalendar()[1]
            logger.info(f"Current date: {now}, Week: {current_week}")

            # Get to Monday of current week
            monday = now - timedelta(days=now.weekday())

            if is_next_week:
                # Move to next Monday
                target_date = monday + timedelta(days=7)
            else:
                target_date = monday

            target_week = target_date.isocalendar()[1]
            logger.info(f"Target date: {target_date}, Week: {target_week}")
            return target_date
        except Exception as e:
            logger.error(
                f"Error in _get_week_dates: {str(e)}\n{traceback.format_exc()}"
            )
            raise

    async def get_day_schedule(
        self, nickname: str, target_date: datetime
    ) -> Optional[Dict]:
        """Get schedule for a specific day.

        Args:
            nickname: Student's nickname
            target_date: The date to get schedule for

        Returns:
            Optional[Dict]: Schedule data if found
        """
        try:
            logger.info(f"Getting schedule for {nickname} on {target_date}")

            # Get schedule ID in YYYYWW format
            year = target_date.strftime("%Y")
            week = str(target_date.isocalendar()[1]).zfill(2)
            schedule_id = f"{year}{week}"
            logger.info(f"Looking for schedule {schedule_id} for {nickname}")

            # Get schedule from database
            schedule = await self.repository.get_schedule_by_id(schedule_id, nickname)
            if not schedule:
                logger.warning(f"No schedule found for {schedule_id}")
                return None

            # Find the specific day
            day_id = target_date.strftime("%Y%m%d")
            logger.debug(f"Looking for day {day_id}")
            day = next((d for d in schedule.days if d.id == day_id), None)
            if not day:
                logger.warning(f"No day found for {day_id}")
                return None

            # Convert to display format
            return {
                "lessons": [
                    {
                        "time": self._get_lesson_time(lesson.index),
                        "subject": lesson.subject,
                        "room": lesson.room,
                        "teacher": "TBD",  # TODO: Add teacher information to database
                    }
                    for lesson in sorted(day.lessons, key=lambda x: x.index)
                ]
            }
        except Exception as e:
            logger.error(
                f"Error in get_day_schedule: {str(e)}\n{traceback.format_exc()}"
            )
            raise

    async def get_week_schedule(
        self, nickname: str, start_date: datetime, is_next_week: bool = False
    ) -> Optional[Dict]:
        """Get schedule for a week.

        Args:
            nickname: Student's nickname
            start_date: Current date
            is_next_week: Whether to get next week's schedule

        Returns:
            Optional[Dict]: Schedule data if found
        """
        try:
            logger.info(
                f"Getting week schedule for {nickname}, is_next_week: {is_next_week}"
            )
            logger.info(f"Start date: {start_date}")

            # Get the appropriate week start date
            week_start = self._get_week_dates(is_next_week)
            if not week_start:
                logger.error("Failed to get week start date")
                return None

            logger.info(f"Week start date: {week_start}")

            # Get schedule ID in YYYYWW format
            year = week_start.strftime("%Y")
            week = str(week_start.isocalendar()[1]).zfill(2)
            schedule_id = f"{year}{week}"
            logger.info(f"Looking for schedule {schedule_id} for {nickname}")

            # Get schedule from database
            schedule = await self.repository.get_schedule_by_id(schedule_id, nickname)
            if not schedule:
                logger.warning(f"No schedule found for {schedule_id}")
                return None

            # Convert to display format
            week_schedule = {}
            current_date = week_start

            # Process each weekday
            for _ in range(5):  # Monday to Friday
                day_id = current_date.strftime("%Y%m%d")
                logger.debug(f"Looking for day {day_id}")
                day = next((d for d in schedule.days if d.id == day_id), None)

                if day:
                    week_schedule[current_date.strftime("%A")] = [
                        {
                            "time": self._get_lesson_time(lesson.index),
                            "subject": lesson.subject,
                            "room": lesson.room,
                        }
                        for lesson in sorted(day.lessons, key=lambda x: x.index)
                    ]
                    logger.debug(f"Found {len(day.lessons)} lessons for {day_id}")
                else:
                    logger.debug(f"No lessons found for {day_id}")
                    week_schedule[current_date.strftime("%A")] = []

                current_date += timedelta(days=1)

            return week_schedule
        except Exception as e:
            logger.error(
                f"Error in get_week_schedule: {str(e)}\n{traceback.format_exc()}"
            )
            raise
