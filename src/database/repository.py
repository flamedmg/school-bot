"""Repository for schedule data"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Tuple
from .enums import ChangeType
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pathlib import Path
from loguru import logger
from . import models
from .types import ScheduleChanges, DayChanges, LessonChange, AnnouncementChange
from ..schedule.schema import (
    Schedule as ScheduleModel,
    SchoolDay,
    Lesson,
    Homework,
    Link,
    Attachment,
    Announcement,
    AnnouncementType,
)


class ScheduleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_attachment_by_id(self, unique_id: str) -> Optional[models.Attachment]:
        """
        Get an attachment by its unique ID.

        Args:
            unique_id: The unique identifier of the attachment

        Returns:
            Optional[models.Attachment]: The attachment if found, None otherwise
        """
        stmt = select(models.Attachment).where(models.Attachment.unique_id == unique_id)
        result = await self.session.scalars(stmt)
        return result.first()

    async def get_attachment_path(self, unique_id: str) -> Optional[Path]:
        """
        Get the file path for an attachment by its unique ID.
        
        Args:
            unique_id: The unique identifier of the attachment

        Returns:
            Optional[Path]: The path where the attachment should be stored, or None if attachment not found
        """
        attachment = await self.get_attachment_by_id(unique_id)
        if attachment:
            return attachment.get_file_path()
        return None

    async def save_schedule(self, schedule: ScheduleModel) -> models.Schedule:
        """Save schedule to database, updating if there are changes"""
        # Pad schedule unique_id to 8 digits
        padded_id = schedule.unique_id.zfill(8)
        db_schedule = await self.get_schedule_by_unique_id(padded_id, schedule.nickname)

        if db_schedule is None:
            # Schedule doesn't exist, create new
            db_schedule = self._create_schedule(schedule)
            self.session.add(db_schedule)
            await self.session.commit()
            await self.session.refresh(db_schedule)
        else:
            # Check for changes before updating
            changes = await self.get_changes(schedule)
            if changes.has_changes():
                # Update only if there are changes
                await self._update_schedule(db_schedule, schedule)
                await self.session.commit()
                await self.session.refresh(db_schedule)
                logger.info(f"Schedule {schedule.unique_id} updated with changes.")
            else:
                # No changes detected, skip update
                logger.info(f"No changes detected for schedule {schedule.unique_id}, skipping update.")
        return db_schedule

    async def get_schedule_by_unique_id(
        self, unique_id: str, nickname: str
    ) -> Optional[models.Schedule]:
        """Get schedule by its unique ID and nickname with all relationships loaded"""
        # Ensure unique_id is padded to 8 digits
        padded_id = unique_id.zfill(8)
        stmt = (
            select(models.Schedule)
            .options(
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
                models.Schedule.unique_id == padded_id,
                models.Schedule.nickname == nickname,
            )
        )
        result = await self.session.scalars(stmt)
        return result.first()

    def _check_lesson_order(
        self, new_lessons: List[Lesson], db_lessons: List[models.Lesson]
    ) -> bool:
        """Check if lesson order has changed"""
        # Create mappings of index to subject for both lists
        new_order = {l.index: l.subject for l in new_lessons}
        db_order = {l.index: l.subject for l in db_lessons}

        # Compare the subjects at each index
        for index in new_order:
            if index in db_order and new_order[index] != db_order[index]:
                return True

        return False

    def _check_announcements(
        self,
        new_announcements: List[Announcement],
        db_announcements: List[models.Announcement],
    ) -> List[AnnouncementChange]:
        """Check for changes in announcements"""
        changes = []
        new_ids = {a.unique_id for a in new_announcements}
        db_ids = {a.unique_id for a in db_announcements}

        new_lookup = {a.unique_id: a for a in new_announcements}
        db_lookup = {a.unique_id: a for a in db_announcements}

        # Added announcements
        for announcement_id in new_ids - db_ids:
            announcement = new_lookup[announcement_id]
            # Handle different announcement types
            announcement_text = (
                announcement.description
                if announcement.type == AnnouncementType.BEHAVIOR
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
                if announcement.type == AnnouncementType.BEHAVIOR
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

    async def get_changes(self, schedule: ScheduleModel) -> ScheduleChanges:
        """Compare schedule with database version and return changes"""
        padded_id = schedule.unique_id.zfill(8)
        db_schedule = await self.get_schedule_by_unique_id(padded_id, schedule.nickname)

        changes = ScheduleChanges(
            schedule_id=schedule.unique_id, structure_changed=False, days=[]
        )

        if not db_schedule:
            # If there is no existing schedule, all data is new
            changes.structure_changed = True
            return changes

        # Compare each day
        for new_day in schedule.days:
            db_day = next(
                (d for d in db_schedule.days if d.unique_id == new_day.unique_id), None
            )
            if not db_day:
                changes.structure_changed = True
                continue

            day_changes = DayChanges(
                day_id=new_day.unique_id, lessons=[], homework=[], announcements=[]
            )

            # Create a map to track changes by lesson_id
            lesson_changes_map = {}

            # Check lesson order first
            if self._check_lesson_order(new_day.lessons, db_day.lessons):
                order_change = LessonChange(
                    lesson_id=new_day.unique_id, order_changed=True
                )
                day_changes.lessons.append(order_change)

            # Create lookup dictionary for database lessons
            db_lookup = {l.index: l for l in db_day.lessons}

            # Process all changes for each lesson
            for new_lesson in new_day.lessons:
                if new_lesson.index in db_lookup:
                    db_lesson = db_lookup[new_lesson.index]
                    lesson_id = new_lesson.unique_id

                    # Create or get the change object for this lesson
                    if lesson_id not in lesson_changes_map:
                        lesson_changes_map[lesson_id] = LessonChange(
                            lesson_id=lesson_id
                        )

                    change = lesson_changes_map[lesson_id]

                    # Check mark changes
                    if new_lesson.mark != db_lesson.mark and (
                        new_lesson.mark is not None or db_lesson.mark is not None
                    ):
                        change.mark_changed = True
                        change.old_mark = db_lesson.mark
                        change.new_mark = new_lesson.mark

                    # Check subject changes
                    if new_lesson.subject != db_lesson.subject:
                        change.subject_changed = True
                        change.old_subject = db_lesson.subject
                        change.new_subject = new_lesson.subject

            # Add all lesson changes to the day
            day_changes.lessons.extend(lesson_changes_map.values())

            # Process announcement changes
            announcement_changes = self._check_announcements(
                new_day.announcements, db_day.announcements
            )
            day_changes.announcements.extend(announcement_changes)

            if (
                day_changes.lessons
                or day_changes.homework
                or day_changes.announcements
            ):
                changes.days.append(day_changes)

        return changes

    def _create_schedule(self, schedule: ScheduleModel) -> models.Schedule:
        """Create new schedule in database"""
        unique_id = schedule.unique_id.zfill(8)
        db_schedule = models.Schedule(unique_id=unique_id, nickname=schedule.nickname)

        # First, ensure all days in the schedule have their announcements properly linked
        for day in schedule.days:
            # Set day reference for all announcements in this day
            for announcement in day.announcements:
                announcement._day = day

            # Create the database objects
            db_day = models.SchoolDay(
                unique_id=day.date.strftime("%Y%m%d"),
                date=day.date,
            )
            db_day.schedule = db_schedule

            for lesson in day.lessons:
                db_lesson = self._create_lesson(lesson)
                db_lesson.day = db_day
                db_day.lessons.append(db_lesson)

            for announcement in day.announcements:
                db_announcement = self._create_announcement(announcement)
                db_announcement.day = db_day
                db_day.announcements.append(db_announcement)

            db_schedule.days.append(db_day)

        return db_schedule

    async def _update_schedule(
        self, db_schedule: models.Schedule, schedule: ScheduleModel
    ):
        """Update existing schedule with new data without deleting and recreating."""
        db_schedule.nickname = schedule.nickname

        # Create a mapping of existing days by unique_id
        db_days_map = {day.unique_id: day for day in db_schedule.days}

        for day in schedule.days:
            day_unique_id = day.date.strftime("%Y%m%d")
            if day_unique_id in db_days_map:
                # Update existing day
                db_day = db_days_map[day_unique_id]
                await self._update_day(db_day, day)
            else:
                # Add new day
                db_day = models.SchoolDay(
                    unique_id=day_unique_id,
                    date=day.date,
                    schedule=db_schedule,
                )
                db_schedule.days.append(db_day)
                await self._update_day(db_day, day)

        # Remove days that are no longer in the schedule
        incoming_day_ids = set(d.date.strftime("%Y%m%d") for d in schedule.days)
        db_day_ids = set(db_days_map.keys())
        days_to_remove = db_day_ids - incoming_day_ids
        for day_id in days_to_remove:
            db_day = db_days_map[day_id]
            await self.session.delete(db_day)

    async def _update_day(self, db_day: models.SchoolDay, day: SchoolDay):
        """Update existing day with new data without deleting and recreating content."""
        # Update lessons
        db_lessons_map = {lesson.unique_id: lesson for lesson in db_day.lessons}
        incoming_lessons = []

        for lesson in day.lessons:
            if lesson.unique_id in db_lessons_map:
                db_lesson = db_lessons_map[lesson.unique_id]
                await self._update_lesson(db_lesson, lesson)
                incoming_lessons.append(db_lesson)
            else:
                db_lesson = self._create_lesson(lesson)
                db_lesson.day = db_day
                incoming_lessons.append(db_lesson)

        # Remove lessons that are no longer in the schedule
        incoming_lesson_ids = set(lesson.unique_id for lesson in day.lessons)
        db_lesson_ids = set(db_lessons_map.keys())
        lessons_to_remove = db_lesson_ids - incoming_lesson_ids
        for lesson_id in lessons_to_remove:
            db_lesson = db_lessons_map[lesson_id]
            await self.session.delete(db_lesson)

        db_day.lessons = incoming_lessons

        # Update announcements similarly
        db_announcements_map = {ann.unique_id: ann for ann in db_day.announcements}
        incoming_announcements = []

        for announcement in day.announcements:
            if announcement.unique_id in db_announcements_map:
                db_announcement = db_announcements_map[announcement.unique_id]
                self._update_announcement(db_announcement, announcement)
                incoming_announcements.append(db_announcement)
            else:
                db_announcement = self._create_announcement(announcement)
                db_announcement.day = db_day
                incoming_announcements.append(db_announcement)

        # Remove announcements that are no longer in the schedule
        incoming_announcement_ids = set(ann.unique_id for ann in day.announcements)
        db_announcement_ids = set(db_announcements_map.keys())
        announcements_to_remove = db_announcement_ids - incoming_announcement_ids
        for ann_id in announcements_to_remove:
            db_announcement = db_announcements_map[ann_id]
            await self.session.delete(db_announcement)

        db_day.announcements = incoming_announcements

    async def _update_lesson(self, db_lesson: models.Lesson, lesson: Lesson):
        """Update existing lesson with new data without recreating."""
        db_lesson.index = lesson.index
        db_lesson.subject = lesson.subject
        db_lesson.room = lesson.room
        db_lesson.topic = lesson.topic
        db_lesson.mark = lesson.mark

        # Update topic attachments
        self._update_attachments(
            db_lesson.topic_attachments,
            lesson.topic_attachments,
            parent='lesson',
            db_lesson=db_lesson
        )

        if lesson.homework:
            if db_lesson.homework:
                self._update_homework(db_lesson.homework, lesson.homework)
            else:
                db_lesson.homework = self._create_homework(lesson.homework)
                db_lesson.homework.lesson = db_lesson
        else:
            if db_lesson.homework:
                await self.session.delete(db_lesson.homework)
                db_lesson.homework = None

    def _update_homework(self, db_homework: models.Homework, homework: Homework):
        """Update existing homework with new data without recreating."""
        db_homework.text = homework.text

        # Update links
        self._update_links(db_homework.links, homework.links)

        # Update attachments
        self._update_attachments(
            db_homework.attachments,
            homework.attachments,
            parent='homework',
            db_homework=db_homework
        )

    def _update_attachments(self, db_attachments, new_attachments, parent, db_lesson=None, db_homework=None):
        """Update attachments list without recreating."""
        db_attachments_map = {att.unique_id: att for att in db_attachments}
        incoming_attachments = []

        for attachment in new_attachments:
            if attachment.unique_id in db_attachments_map:
                db_attachment = db_attachments_map[attachment.unique_id]
                db_attachment.filename = attachment.filename
                db_attachment.url = attachment.url
                incoming_attachments.append(db_attachment)
            else:
                db_attachment = self._create_attachment(attachment)
                if parent == 'lesson' and db_lesson:
                    db_attachment.lesson = db_lesson
                elif parent == 'homework' and db_homework:
                    db_attachment.homework = db_homework
                incoming_attachments.append(db_attachment)

        # Remove attachments that are no longer present
        incoming_attachment_ids = set(att.unique_id for att in new_attachments)
        db_attachment_ids = set(db_attachments_map.keys())
        attachments_to_remove = db_attachment_ids - incoming_attachment_ids
        for att_id in attachments_to_remove:
            db_attachment = db_attachments_map[att_id]
            self.session.delete(db_attachment)

        # Update the list in place
        db_attachments[:] = incoming_attachments

    def _update_links(self, db_links, new_links):
        """Update links list without recreating."""
        db_links_map = {link.unique_id: link for link in db_links}
        incoming_links = []

        for link in new_links:
            if link.unique_id in db_links_map:
                db_link = db_links_map[link.unique_id]
                db_link.original_url = link.original_url
                db_link.destination_url = link.destination_url
                incoming_links.append(db_link)
            else:
                db_link = self._create_link(link)
                incoming_links.append(db_link)

        # Remove links that are no longer present
        incoming_link_ids = set(link.unique_id for link in new_links)
        db_link_ids = set(db_links_map.keys())
        links_to_remove = db_link_ids - incoming_link_ids
        for link_id in links_to_remove:
            db_link = db_links_map[link_id]
            self.session.delete(db_link)

        # Update the list in place
        db_links[:] = incoming_links

    def _create_lesson(self, lesson: Lesson) -> models.Lesson:
        """Create a lesson with all its data"""
        db_lesson = models.Lesson(
            unique_id=lesson.unique_id,
            index=lesson.index,
            subject=lesson.subject,
            room=lesson.room,
            topic=lesson.topic,
            mark=lesson.mark,
        )

        # Add topic attachments - ensure they have _day reference
        for attachment in lesson.topic_attachments:
            if not attachment._day and lesson._day:
                attachment._day = lesson._day
            db_attachment = self._create_attachment(attachment)
            db_attachment.lesson = db_lesson
            db_lesson.topic_attachments.append(db_attachment)

        if lesson.homework:
            # Ensure homework has _day reference
            if not lesson.homework._day and lesson._day:
                lesson.homework._day = lesson._day
                # Also ensure homework's attachments have _day reference
                for attachment in lesson.homework.attachments:
                    if not attachment._day:
                        attachment._day = lesson._day
            db_lesson.homework = self._create_homework(lesson.homework)
            db_lesson.homework.lesson = db_lesson

        return db_lesson

    def _create_homework(self, homework: Homework) -> models.Homework:
        """Create homework with all its data"""
        db_homework = models.Homework(unique_id=homework.unique_id, text=homework.text)

        for link in homework.links:
            db_link = self._create_link(link)
            db_link.homework = db_homework
            db_homework.links.append(db_link)

        for attachment in homework.attachments:
            db_attachment = self._create_attachment(attachment)
            db_attachment.homework = db_homework
            db_homework.attachments.append(db_attachment)

        return db_homework

    def _create_link(self, link: Link) -> models.Link:
        """Create a link with all its data"""
        return models.Link(
            unique_id=link.unique_id,
            original_url=link.original_url,
            destination_url=link.destination_url,
        )

    def _create_attachment(self, attachment: Attachment) -> models.Attachment:
        """Create an attachment with all its data"""
        return models.Attachment(
            unique_id=attachment.unique_id,
            filename=attachment.filename,
            url=attachment.url,
        )

    def _update_announcement(
        self, db_announcement: models.Announcement, announcement: Announcement
    ):
        """Update existing announcement with new data"""
        db_announcement.type = announcement.type
        db_announcement.text = announcement.text
        db_announcement.behavior_type = announcement.behavior_type
        db_announcement.description = announcement.description
        db_announcement.rating = announcement.rating
        db_announcement.subject = announcement.subject

    def _create_announcement(self, announcement: Announcement) -> models.Announcement:
        """Create an announcement with all its data"""
        # Ensure announcement has day reference for unique_id generation
        if not announcement._day:
            raise ValueError("Announcement must have day reference")
            
        return models.Announcement(
            unique_id=announcement.unique_id,
            type=announcement.type.value,  # Store the enum value, not the enum itself
            text=announcement.text,
            behavior_type=announcement.behavior_type,
            description=announcement.description,
            rating=announcement.rating,
            subject=announcement.subject,
        )
