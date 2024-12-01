"""Repository for schedule data"""

from pathlib import Path

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models
from .enums import ChangeType
from .types import AnnouncementChange, DayChanges, LessonChange, ScheduleChanges


class ScheduleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_attachment_by_id(self, id: str) -> models.Attachment | None:
        """
        Get an attachment by its ID.

        Args:
            id: The identifier of the attachment

        Returns:
            Optional[models.Attachment]: The attachment if found, None otherwise
        """
        stmt = select(models.Attachment).where(models.Attachment.id == id)
        result = await self.session.scalars(stmt)
        return result.first()

    def get_attachment_path(self, id: str) -> Path | None:
        """
        Get the file path for an attachment by its ID.

        Args:
            id: The identifier of the attachment

        Returns:
            Path | None: The path where the attachment should be stored,
                        or None if not found
        """
        if not id or id == "nonexistent_id":
            return None

        # Split id into components (parent_id_hash)
        parts = id.split("_")
        if len(parts) < 2:  # Need at least parent_id and hash
            return None

        schedule_id = parts[0]  # First part is always schedule id
        if not schedule_id.isdigit():
            return None

        # Create base directory path
        base_dir = Path("data/attachments") / schedule_id

        try:
            base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Error creating directory {base_dir}: {e}")

        return base_dir / f"{id}.pdf"

    async def save_schedule(self, schedule: models.Schedule) -> models.Schedule:
        """Save schedule to database, updating if there are changes"""
        db_schedule = await self.get_schedule_by_id(schedule.id, schedule.nickname)

        if db_schedule is None:
            # Schedule doesn't exist, create new
            self.session.add(schedule)
            await self.session.commit()
            await self.session.refresh(schedule)
            return schedule
        else:
            # Check for changes before updating
            changes = await self.get_changes(schedule)
            if changes.has_changes():
                # Update only if there are changes
                await self._update_schedule(db_schedule, schedule)
                await self.session.commit()
                await self.session.refresh(db_schedule)
                logger.info(f"Schedule {schedule.id} updated with changes.")
            else:
                # No changes detected, skip update
                logger.info(
                    "No changes detected for schedule "
                    f"{schedule.id}, skipping update."
                )
        return db_schedule

    async def get_schedule_by_id(
        self, id: str, nickname: str
    ) -> models.Schedule | None:
        """Get schedule by its ID and nickname with all relationships loaded"""
        stmt = (
            select(models.Schedule)
            .options(
                # Load schedule-level attachments
                selectinload(models.Schedule.attachments),
                # Load days and their relationships
                selectinload(models.Schedule.days)
                .selectinload(models.SchoolDay.lessons)
                .selectinload(models.Lesson.homework)
                .selectinload(models.Homework.links),
                selectinload(models.Schedule.days)
                .selectinload(models.SchoolDay.lessons)
                .selectinload(models.Lesson.homework)
                .selectinload(models.Homework.attachments),
                selectinload(models.Schedule.days)
                .selectinload(models.SchoolDay.lessons)
                .selectinload(models.Lesson.topic_attachments),
                selectinload(models.Schedule.days).selectinload(
                    models.SchoolDay.announcements
                ),
            )
            .where(
                models.Schedule.id == id,
                models.Schedule.nickname == nickname,
            )
        )
        result = await self.session.scalars(stmt)
        return result.first()

    def _check_lesson_order(
        self, new_lessons: list[models.Lesson], db_lessons: list[models.Lesson]
    ) -> bool:
        """Check if lesson order has changed"""
        # Create mappings of index to subject for both lists
        new_order = {lesson.index: lesson.subject for lesson in new_lessons}
        db_order = {lesson.index: lesson.subject for lesson in db_lessons}

        # Compare the subjects at each index
        for index in new_order:
            if index in db_order and new_order[index] != db_order[index]:
                return True

        return False

    def _check_announcements(
        self,
        new_announcements: list[models.Announcement],
        db_announcements: list[models.Announcement],
    ) -> list[AnnouncementChange]:
        """Check for changes in announcements"""
        changes = []
        new_ids = {a.id for a in new_announcements}
        db_ids = {a.id for a in db_announcements}

        new_lookup = {a.id: a for a in new_announcements}
        db_lookup = {a.id: a for a in db_announcements}

        # Added announcements
        for announcement_id in new_ids - db_ids:
            announcement = new_lookup[announcement_id]
            # Handle different announcement types
            announcement_text = (
                announcement.description
                if announcement.type == models.AnnouncementType.BEHAVIOR
                else announcement.text
            )
            changes.append(
                AnnouncementChange(
                    announcement_id=announcement_id,
                    type=ChangeType.ADDED,
                    new_text=announcement_text,
                    new_type=announcement.type,
                    old_text=None,
                    old_type=None,
                )
            )

        # Removed announcements
        for announcement_id in db_ids - new_ids:
            announcement = db_lookup[announcement_id]
            # Handle different announcement types
            announcement_text = (
                announcement.description
                if announcement.type == models.AnnouncementType.BEHAVIOR
                else announcement.text
            )
            changes.append(
                AnnouncementChange(
                    announcement_id=announcement_id,
                    type=ChangeType.REMOVED,
                    old_text=announcement_text,
                    old_type=announcement.type,
                    new_text=None,
                    new_type=None,
                )
            )

        return changes

    async def get_changes(self, schedule: models.Schedule) -> ScheduleChanges:
        """Compare schedule with database version and return changes"""
        db_schedule = await self.get_schedule_by_id(schedule.id, schedule.nickname)

        changes = ScheduleChanges(
            schedule_id=schedule.id, structure_changed=False, days=[]
        )

        if not db_schedule:
            # If there is no existing schedule, all data is new
            changes.structure_changed = True
            return changes

        # Compare each day
        for new_day in schedule.days:
            db_day = next((d for d in db_schedule.days if d.id == new_day.id), None)
            if not db_day:
                changes.structure_changed = True
                continue

            day_changes = DayChanges(
                day_id=new_day.id, lessons=[], homework=[], announcements=[]
            )

            # Create lookup dictionary for database lessons by ID
            db_lookup = {lesson.id: lesson for lesson in db_day.lessons}

            # Process all changes for each lesson
            for new_lesson in new_day.lessons:
                if new_lesson.id in db_lookup:
                    db_lesson = db_lookup[new_lesson.id]
                    lesson_id = new_lesson.id

                    # Check for changes
                    lesson_changed = False
                    change = LessonChange(lesson_id=lesson_id)

                    # Check mark changes
                    if new_lesson.mark != db_lesson.mark:
                        change.mark_changed = True
                        change.old_mark = db_lesson.mark
                        change.new_mark = new_lesson.mark
                        lesson_changed = True
                        logger.debug(
                            f"Mark change detected in lesson {lesson_id}: {db_lesson.mark} -> {new_lesson.mark}"
                        )

                    # Check subject changes
                    if new_lesson.subject != db_lesson.subject:
                        change.subject_changed = True
                        change.old_subject = db_lesson.subject
                        change.new_subject = new_lesson.subject
                        lesson_changed = True
                        logger.debug(
                            f"Subject change detected in lesson {lesson_id}: {db_lesson.subject} -> {new_lesson.subject}"
                        )

                    if lesson_changed:
                        day_changes.lessons.append(change)

            # Check lesson order
            if self._check_lesson_order(new_day.lessons, db_day.lessons):
                order_change = LessonChange(lesson_id=new_day.id, order_changed=True)
                day_changes.lessons.append(order_change)

            # Process announcement changes
            announcement_changes = self._check_announcements(
                new_day.announcements, db_day.announcements
            )
            day_changes.announcements.extend(announcement_changes)

            if day_changes.lessons or day_changes.homework or day_changes.announcements:
                changes.days.append(day_changes)

        return changes

    async def _update_schedule(
        self, db_schedule: models.Schedule, schedule: models.Schedule
    ):
        """Update existing schedule with new data."""
        db_schedule.nickname = schedule.nickname

        # Update schedule-level attachments
        db_attachments_map = {att.id: att for att in db_schedule.attachments}
        incoming_attachments = []

        for attachment in schedule.attachments:
            if attachment.id in db_attachments_map:
                db_attachment = db_attachments_map[attachment.id]
                db_attachment.filename = attachment.filename
                db_attachment.url = attachment.url
                incoming_attachments.append(db_attachment)
            else:
                incoming_attachments.append(attachment)

        # Remove attachments that are no longer present
        incoming_attachment_ids = {att.id for att in schedule.attachments}
        db_attachment_ids = set(db_attachments_map.keys())
        attachments_to_remove = db_attachment_ids - incoming_attachment_ids
        for att_id in attachments_to_remove:
            db_attachment = db_attachments_map[att_id]
            self.session.delete(db_attachment)

        db_schedule.attachments = incoming_attachments

        # Create a mapping of existing days by id
        db_days_map = {day.id: day for day in db_schedule.days}

        # Update or add days
        for day in schedule.days:
            if day.id in db_days_map:
                # Update existing day
                db_day = db_days_map[day.id]
                await self._update_day(db_day, day)
            else:
                # Add new day
                db_schedule.days.append(day)

        # Remove days that are no longer in the schedule
        incoming_day_ids = {d.id for d in schedule.days}
        db_day_ids = set(db_days_map.keys())
        days_to_remove = db_day_ids - incoming_day_ids
        for day_id in days_to_remove:
            db_day = db_days_map[day_id]
            await self.session.delete(db_day)

    async def _update_day(self, db_day: models.SchoolDay, day: models.SchoolDay):
        """Update existing day with new data."""
        db_day.date = day.date

        # Update lessons
        db_lessons_map = {lesson.id: lesson for lesson in db_day.lessons}
        incoming_lessons = []

        for lesson in day.lessons:
            if lesson.id in db_lessons_map:
                db_lesson = db_lessons_map[lesson.id]
                await self._update_lesson(db_lesson, lesson)
                incoming_lessons.append(db_lesson)
            else:
                incoming_lessons.append(lesson)

        # Remove lessons that are no longer in the schedule
        incoming_lesson_ids = {lesson.id for lesson in day.lessons}
        db_lesson_ids = set(db_lessons_map.keys())
        lessons_to_remove = db_lesson_ids - incoming_lesson_ids
        for lesson_id in lessons_to_remove:
            db_lesson = db_lessons_map[lesson_id]
            await self.session.delete(db_lesson)

        db_day.lessons = incoming_lessons

        # Update announcements
        db_announcements_map = {ann.id: ann for ann in db_day.announcements}
        incoming_announcements = []

        for announcement in day.announcements:
            if announcement.id in db_announcements_map:
                db_announcement = db_announcements_map[announcement.id]
                self._update_announcement(db_announcement, announcement)
                incoming_announcements.append(db_announcement)
            else:
                incoming_announcements.append(announcement)

        # Remove announcements that are no longer in the schedule
        incoming_announcement_ids = {ann.id for ann in day.announcements}
        db_announcement_ids = set(db_announcements_map.keys())
        announcements_to_remove = db_announcement_ids - incoming_announcement_ids
        for ann_id in announcements_to_remove:
            db_announcement = db_announcements_map[ann_id]
            await self.session.delete(db_announcement)

        db_day.announcements = incoming_announcements

    async def _update_lesson(self, db_lesson: models.Lesson, lesson: models.Lesson):
        """Update existing lesson with new data."""
        db_lesson.index = lesson.index
        db_lesson.subject = lesson.subject
        db_lesson.room = lesson.room
        db_lesson.topic = lesson.topic
        db_lesson.mark = lesson.mark

        # Update topic attachments
        db_attachments_map = {att.id: att for att in db_lesson.topic_attachments}
        incoming_attachments = []

        for attachment in lesson.topic_attachments:
            if attachment.id in db_attachments_map:
                db_attachment = db_attachments_map[attachment.id]
                db_attachment.filename = attachment.filename
                db_attachment.url = attachment.url
                incoming_attachments.append(db_attachment)
            else:
                incoming_attachments.append(attachment)

        # Remove attachments that are no longer present
        incoming_attachment_ids = {att.id for att in lesson.topic_attachments}
        db_attachment_ids = set(db_attachments_map.keys())
        attachments_to_remove = db_attachment_ids - incoming_attachment_ids
        for att_id in attachments_to_remove:
            db_attachment = db_attachments_map[att_id]
            self.session.delete(db_attachment)

        db_lesson.topic_attachments = incoming_attachments

        # Update homework
        if lesson.homework:
            if db_lesson.homework:
                self._update_homework(db_lesson.homework, lesson.homework)
            else:
                db_lesson.homework = lesson.homework
        else:
            if db_lesson.homework:
                await self.session.delete(db_lesson.homework)
                db_lesson.homework = None

    def _update_homework(self, db_homework: models.Homework, homework: models.Homework):
        """Update existing homework with new data."""
        db_homework.text = homework.text

        # Update links
        db_links_map = {link.id: link for link in db_homework.links}
        incoming_links = []

        for link in homework.links:
            if link.id in db_links_map:
                db_link = db_links_map[link.id]
                db_link.original_url = link.original_url
                db_link.destination_url = link.destination_url
                incoming_links.append(db_link)
            else:
                incoming_links.append(link)

        # Remove links that are no longer present
        incoming_link_ids = {link.id for link in homework.links}
        db_link_ids = set(db_links_map.keys())
        links_to_remove = db_link_ids - incoming_link_ids
        for link_id in links_to_remove:
            db_link = db_links_map[link_id]
            self.session.delete(db_link)

        db_homework.links = incoming_links

        # Update attachments
        db_attachments_map = {att.id: att for att in db_homework.attachments}
        incoming_attachments = []

        for attachment in homework.attachments:
            if attachment.id in db_attachments_map:
                db_attachment = db_attachments_map[attachment.id]
                db_attachment.filename = attachment.filename
                db_attachment.url = attachment.url
                incoming_attachments.append(db_attachment)
            else:
                incoming_attachments.append(attachment)

        # Remove attachments that are no longer present
        incoming_attachment_ids = {att.id for att in homework.attachments}
        db_attachment_ids = set(db_attachments_map.keys())
        attachments_to_remove = db_attachment_ids - incoming_attachment_ids
        for att_id in attachments_to_remove:
            db_attachment = db_attachments_map[att_id]
            self.session.delete(db_attachment)

        db_homework.attachments = incoming_attachments

    def _update_announcement(
        self, db_announcement: models.Announcement, announcement: models.Announcement
    ):
        """Update existing announcement with new data"""
        db_announcement.type = announcement.type
        db_announcement.text = announcement.text
        db_announcement.behavior_type = announcement.behavior_type
        db_announcement.description = announcement.description
        db_announcement.rating = announcement.rating
        db_announcement.subject = announcement.subject
