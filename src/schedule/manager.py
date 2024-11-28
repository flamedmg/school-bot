from datetime import datetime
from typing import List, Dict
from faststream.redis import RedisBroker
from loguru import logger
import os
import traceback

from src.schedule.crawler import ScheduleCrawler
from src.schedule.exceptions import CrawlException
from src.database.repository import ScheduleRepository
from src.events.event_types import CrawlErrorEvent, EventTopics
from src.schedule.preprocess import create_default_pipeline
from src.schedule.schema import Schedule
from src.events.types import AttachmentEvent


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
        self._changes_summary = {
            "lessons_changed": 0,
            "marks_changed": 0,
            "subjects_changed": 0,
            "announcements_added": 0,
            "announcements_removed": 0,
            "subject_changes_details": [],  # List to store detailed subject changes
        }
        self._schedules_processed = 0
        self.crawler = ScheduleCrawler(username, password, nickname)

    def _convert_cookies_to_dict(self, cookies: List[Dict]) -> Dict[str, str]:
        """Convert cookies from list format to dictionary format."""
        return {cookie["name"]: cookie["value"] for cookie in cookies}

    async def process_schedules(self):
        """Main process to handle schedule crawling and change detection."""
        logger.info("Starting schedule processing...")

        try:
            raw_schedules = await self._fetch_schedules()
            await self._process_raw_schedules(raw_schedules)
            self._log_processing_summary()

        except CrawlException as e:
            await self._handle_crawl_error(e)
            raise

        except Exception as e:
            await self._handle_unexpected_error(e)
            raise

    async def _fetch_schedules(self) -> List[tuple]:
        """Fetch schedules from the crawler."""
        return await self.crawler.get_schedules()

    async def _process_raw_schedules(self, raw_schedules: List[tuple]):
        """Process raw schedules through the pipeline."""
        pipeline = create_default_pipeline(nickname=self.nickname)

        # Only process current and past week (first two items)
        for raw_data, html_content in raw_schedules:
            try:
                processed_data = pipeline.execute(raw_data)
                if processed_data and len(processed_data) > 0:
                    # Process attachments from the processed data
                    attachments = processed_data[0].get("attachments", [])
                    cookies_dict = self._convert_cookies_to_dict(self.crawler.cookies)

                    # Debug log processed data and attachments
                    logger.debug("Processed data structure:")
                    logger.debug(processed_data)
                    logger.debug("Attachments from processed data:")
                    logger.debug(attachments)

                    for attachment in attachments:
                        # Debug log attachment data before creating event
                        logger.debug("Creating event for attachment:")
                        logger.debug(attachment)

                        event = AttachmentEvent(
                            student_nickname=self.nickname,
                            filename=attachment["filename"],
                            url=attachment["url"],
                            cookies=cookies_dict,
                            schedule_id=attachment["schedule_id"],
                            subject=attachment["subject"],
                            lesson_number=attachment["lesson_number"],
                            day_id=attachment["day_id"],
                        )
                        await self.broker.publish(event, EventTopics.NEW_ATTACHMENT)
                        logger.debug(
                            f"Emitted attachment event for {attachment['filename']} from {attachment['subject']} lesson {attachment['lesson_number']}"
                        )

                schedule = self._create_schedule_from_data(processed_data)
                if schedule:
                    await self._handle_schedule_changes(schedule)
                self._schedules_processed += 1
            except Exception as e:
                await self._handle_preprocessing_error(e, html_content)
                raise

    def _create_schedule_from_data(self, processed_data: List[dict]) -> Schedule:
        """Create a Schedule object from processed data."""
        try:
            return Schedule(**processed_data[0])
        except (IndexError, TypeError, AttributeError) as e:
            logger.error(f"Invalid schedule data format: {str(e)}")
            return None

    async def _handle_schedule_changes(self, schedule: Schedule):
        """Handle changes detected in a schedule."""
        changes = await self.process_schedule_changes(schedule)
        if changes:
            self._update_changes_summary(changes, schedule)
            await self._publish_changes(schedule, changes)
            await self.save_schedule(schedule)

    def _update_changes_summary(self, changes: Dict, schedule: Schedule):
        """Update the summary of changes and log detailed changes."""
        if changes["lessons_changed"]:
            self._changes_summary["lessons_changed"] += 1
            self._log_lesson_changes(schedule)

        if changes["marks"]:
            self._changes_summary["marks_changed"] += len(changes["marks"])
            self._log_mark_changes(changes["marks"], schedule)

        if changes["subjects"]:
            self._changes_summary["subjects_changed"] += len(changes["subjects"])
            for subject_change in changes["subjects"]:
                # Store detailed subject change information
                change_detail = {
                    "date": schedule.unique_id[:8],  # Extract date from schedule ID
                    "lesson_id": subject_change["lesson_id"],
                    "old_subject": subject_change["old"],
                    "new_subject": subject_change["new"],
                }
                self._changes_summary["subject_changes_details"].append(change_detail)
            self._log_subject_changes(changes["subjects"], schedule)

        if changes["announcements"]["added"]:
            self._changes_summary["announcements_added"] += len(
                changes["announcements"]["added"]
            )
            self._log_announcement_changes(
                "added", changes["announcements"]["added"], schedule
            )

        if changes["announcements"]["removed"]:
            self._changes_summary["announcements_removed"] += len(
                changes["announcements"]["removed"]
            )
            self._log_announcement_changes(
                "removed", changes["announcements"]["removed"], schedule
            )

    def _log_lesson_changes(self, schedule: Schedule):
        """Log lesson order changes."""
        logger.info(f"Lesson order changed in schedule {schedule.unique_id}")

    def _log_mark_changes(self, marks: List[Dict], schedule: Schedule):
        """Log mark changes."""
        for mark in marks:
            logger.info(
                f"Mark changed in schedule {schedule.unique_id}, "
                f"lesson {mark['lesson_id']}: {mark['old']} → {mark['new']}"
            )

    def _log_subject_changes(self, subjects: List[Dict], schedule: Schedule):
        """Log subject changes."""
        for subject in subjects:
            logger.info(
                f"Subject changed in schedule {schedule.unique_id}, "
                f"lesson {subject['lesson_id']}: {subject['old']} → {subject['new']}"
            )

    def _log_announcement_changes(
        self, change_type: str, announcements: List[str], schedule: Schedule
    ):
        """Log announcement changes."""
        logger.info(
            f"{change_type.capitalize()} announcements in schedule {schedule.unique_id}: "
            f"{', '.join(announcements)}"
        )

    def _log_processing_summary(self):
        """Log summary of all changes."""
        # First log the basic summary
        logger.info(
            f"Schedule processing completed. Processed {self._schedules_processed} schedules with changes:\n"
            f"- Lessons order changes: {self._changes_summary['lessons_changed']}\n"
            f"- Mark changes: {self._changes_summary['marks_changed']}\n"
            f"- Subject changes: {self._changes_summary['subjects_changed']}\n"
            f"- Announcements added: {self._changes_summary['announcements_added']}\n"
            f"- Announcements removed: {self._changes_summary['announcements_removed']}"
        )

        # Then log detailed subject changes if any exist
        if self._changes_summary["subject_changes_details"]:
            logger.info("\nDetailed subject changes:")
            for change in self._changes_summary["subject_changes_details"]:
                date = datetime.strptime(change["date"], "%Y%m%d").strftime("%d/%m")
                logger.info(
                    f"{date}: {change['old_subject']} → {change['new_subject']}"
                )

    async def _publish_changes(self, schedule: Schedule, changes: Dict):
        """Publish detected changes to the broker."""
        await self.broker.publish(
            {
                "student_nickname": self.nickname,
                "schedule_id": schedule.unique_id,
                "changes": changes,
            },
            "schedule.change_detected",
        )

    async def _handle_preprocessing_error(self, error: Exception, html_content: str):
        """Handle errors that occur during preprocessing."""
        logger.error(f"Unexpected error in preprocessing step: {str(error)}")
        logger.error(traceback.format_exc())

        date_str = datetime.now().strftime("%Y%m%d")
        error_filename = f"err_schedule_{date_str}.html"
        error_filepath = os.path.join("data", error_filename)
        with open(error_filepath, "w") as error_file:
            error_file.write(html_content)
        logger.info(f"Saved error schedule HTML to {error_filepath}")

    async def _handle_crawl_error(self, error: CrawlException):
        """Handle crawl-specific errors."""
        error_event = CrawlErrorEvent(
            timestamp=error.timestamp,
            student_nickname=error.student_nickname or self.nickname,
            error_type=error.error_type,
            error_message=error.message,
            screenshot_path=error.screenshot_path,
        )
        await self.broker.publish(error_event, EventTopics.CRAWL_ERROR)
        logger.error(f"Crawl error: {error.error_type} - {error.message}")

    async def _handle_unexpected_error(self, error: Exception):
        """Handle unexpected errors."""
        error_event = CrawlErrorEvent(
            timestamp=datetime.now(),
            student_nickname=self.nickname,
            error_type="unexpected_error",
            error_message=str(error),
        )
        await self.broker.publish(error_event, EventTopics.CRAWL_ERROR)
        logger.error(f"Unexpected error: {str(error)}")

    async def process_schedule_changes(self, schedule: Schedule) -> Dict:
        """Process changes for a single schedule using the repository."""
        logger.info(f"Processing changes for schedule {schedule.unique_id}...")
        changes = await self.repository.get_changes(schedule)
        return changes

    async def save_schedule(self, schedule: Schedule):
        """Save a single schedule to the repository."""
        logger.info(f"Saving schedule {schedule.unique_id} to the repository...")
        await self.repository.save_schedule(schedule)
