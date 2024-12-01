import os
import traceback
from datetime import datetime

from faststream.redis import RedisBroker
from loguru import logger

from src.config import settings
from src.database.enums import ChangeType
from src.database.models import Schedule
from src.database.repository import ScheduleRepository
from src.events.event_types import CrawlErrorEvent, EventTopics
from src.events.types import AttachmentEvent
from src.schedule.crawler import ScheduleCrawler
from src.schedule.exceptions import CrawlError
from src.schedule.preprocess import create_default_pipeline


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

    def _convert_cookies_to_dict(self, cookies: list[dict]) -> dict[str, str]:
        """Convert cookies from list format to dictionary format."""
        return {cookie["name"]: cookie["value"] for cookie in cookies}

    async def process_schedules(self):
        """Main process to handle schedule crawling and change detection."""
        logger.info("Starting schedule processing...")

        try:
            raw_schedules = await self._fetch_schedules()
            await self._process_raw_schedules(raw_schedules)
            self._log_processing_summary()

        except CrawlError as e:
            await self._handle_crawl_error(e)
            raise

        except Exception as e:
            await self._handle_unexpected_error(e)
            raise

    async def _fetch_schedules(self) -> list[tuple]:
        """Fetch schedules from the crawler."""
        return await self.crawler.get_schedules()

    async def _process_raw_schedules(self, raw_schedules: list[tuple]):
        """Process raw schedules through the pipeline."""
        pipeline = create_default_pipeline(
            nickname=self.nickname,
            base_url=str(settings.schedule_url),  # Pass schedule URL for attachments
        )

        # Only process current and past week (first two items)
        for raw_data, html_content in raw_schedules:
            try:
                schedule = pipeline.execute(raw_data)
                if isinstance(schedule, Schedule):
                    # Get existing schedule to compare changes
                    existing_schedule = await self.repository.get_schedule_by_id(
                        schedule.id, schedule.nickname
                    )

                    # Process changes
                    changes = await self.repository.get_changes(schedule)
                    if changes.has_changes() or existing_schedule is None:
                        # Process attachments before saving
                        cookies_dict = self._convert_cookies_to_dict(
                            self.crawler.cookies
                        )
                        await self._process_attachments(schedule, cookies_dict)

                        # Update changes summary and publish changes
                        if changes:
                            self._update_changes_summary(changes, schedule)
                            await self._publish_changes(schedule, changes)

                        # Save the schedule after processing
                        await self.repository.save_schedule(schedule)
                        self._schedules_processed += 1
                    else:
                        logger.info(
                            f"No changes detected for schedule {schedule.id}, skipping update."
                        )

            except Exception as e:
                await self._handle_preprocessing_error(e, html_content)
                raise

    async def _process_attachments(self, schedule: Schedule, cookies: dict):
        """Process attachments from all parts of the schedule."""
        # Process schedule-level attachments
        if hasattr(schedule, "attachments"):
            for attachment in schedule.attachments:
                await self._emit_attachment_event(attachment, cookies)

        # Process attachments from days and lessons
        for day in schedule.days:
            for lesson in day.lessons:
                # Process topic attachments
                if hasattr(lesson, "topic_attachments"):
                    for attachment in lesson.topic_attachments:
                        await self._emit_attachment_event(attachment, cookies)

                # Process homework attachments
                if lesson.homework and hasattr(lesson.homework, "attachments"):
                    for attachment in lesson.homework.attachments:
                        await self._emit_attachment_event(attachment, cookies)

    async def _emit_attachment_event(self, attachment, cookies: dict):
        """Emit an attachment event."""

        if not attachment.url.startswith("http"):
            attachment.url = str(settings.schedule_url) + attachment.url
            return

        event = AttachmentEvent(
            student_nickname=self.nickname,
            filename=attachment.filename,
            url=attachment.url,  # URL is already absolute from preprocessor
            cookies=cookies,
            unique_id=attachment.id,
        )
        await self.broker.publish(event, EventTopics.NEW_ATTACHMENT)
        logger.debug(
            f"Emitted attachment event for {attachment.filename} with ID {attachment.id}"
        )

    def _update_changes_summary(self, changes, schedule: Schedule):
        """Update the summary of changes and log detailed changes."""
        # Check for lesson order changes
        for day in changes.days:
            for lesson_change in day.lessons:
                if lesson_change.order_changed:
                    self._changes_summary["lessons_changed"] += 1
                    self._log_lesson_changes(schedule)

                if lesson_change.mark_changed:
                    self._changes_summary["marks_changed"] += 1
                    self._log_mark_changes(
                        [
                            {
                                "lesson_id": lesson_change.lesson_id,
                                "old": lesson_change.old_mark,
                                "new": lesson_change.new_mark,
                            }
                        ],
                        schedule,
                    )

                if lesson_change.subject_changed:
                    self._changes_summary["subjects_changed"] += 1
                    change_detail = {
                        "date": schedule.id[:8],
                        "lesson_id": lesson_change.lesson_id,
                        "old_subject": lesson_change.old_subject,
                        "new_subject": lesson_change.new_subject,
                    }
                    self._changes_summary["subject_changes_details"].append(
                        change_detail
                    )
                    self._log_subject_changes(
                        [
                            {
                                "lesson_id": lesson_change.lesson_id,
                                "old": lesson_change.old_subject,
                                "new": lesson_change.new_subject,
                            }
                        ],
                        schedule,
                    )

            # Process announcements
            for announcement in day.announcements:
                if announcement.type == ChangeType.ADDED:
                    self._changes_summary["announcements_added"] += 1
                    self._log_announcement_changes(
                        "added",
                        [announcement.new_text] if announcement.new_text else [],
                        schedule,
                    )
                elif announcement.type == ChangeType.REMOVED:
                    self._changes_summary["announcements_removed"] += 1
                    self._log_announcement_changes(
                        "removed",
                        [announcement.old_text] if announcement.old_text else [],
                        schedule,
                    )

    def _log_lesson_changes(self, schedule: Schedule):
        """Log lesson order changes."""
        logger.info(f"Lesson order changed in schedule {schedule.id}")

    def _log_mark_changes(self, marks: list[dict], schedule: Schedule):
        """Log mark changes."""
        for mark in marks:
            logger.info(
                f"Mark changed in schedule {schedule.id}, "
                f"lesson {mark['lesson_id']}: {mark['old']} → {mark['new']}"
            )

    def _log_subject_changes(self, subjects: list[dict], schedule: Schedule):
        """Log subject changes."""
        for subject in subjects:
            logger.info(
                f"Subject changed in schedule {schedule.id}, "
                f"lesson {subject['lesson_id']}: {subject['old']} → {subject['new']}"
            )

    def _log_announcement_changes(
        self, change_type: str, announcements: list[str], schedule: Schedule
    ):
        """Log announcement changes."""
        logger.info(
            f"{change_type.capitalize()} announcements in schedule "
            f"{schedule.id}: {', '.join(announcements)}"
        )

    def _log_processing_summary(self):
        """Log summary of all changes."""
        # First log the basic summary
        logger.info(
            "Schedule processing completed. "
            f"Processed {self._schedules_processed} schedules with changes:\n"
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

    async def _publish_changes(self, schedule: Schedule, changes: dict):
        """Publish detected changes to the broker."""
        await self.broker.publish(
            {
                "student_nickname": self.nickname,
                "schedule_id": schedule.id,
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

    async def _handle_crawl_error(self, error: CrawlError):
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

    async def process_schedule_changes(self, schedule: Schedule) -> dict:
        """Process changes for a single schedule using the repository."""
        logger.info(f"Processing changes for schedule {schedule.id}...")
        changes = await self.repository.get_changes(schedule)
        return changes
