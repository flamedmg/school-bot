"""Repository for schedule data"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Tuple
from .enums import ChangeType
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from pathlib import Path
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

    def get_attachment_path(
        self,
        schedule_id: str,
        subject: str,
        lesson_number: str,
        filename: str,
        day_id: str,
    ) -> Path:
        """
        Get the proper path for an attachment file.

        Args:
            schedule_id: Schedule unique ID (YYYYWW)
            subject: Subject name
            lesson_number: Lesson number
            filename: Original filename
            day_id: Unique identifier of the day

        Returns:
            Path object with the proper attachment path
        """
        # Create path: data/attachments/YYYYWW/day_id_subject_lesson_filename
        base_dir = Path("data/attachments") / schedule_id
        base_dir.mkdir(parents=True, exist_ok=True)

        # Clean subject name (remove spaces, lowercase)
        subject_clean = subject.replace(" ", "").lower()

        # Create filename: YYYYMMDD_subject_filename
        unique_filename = f"{day_id}_{subject_clean}{lesson_number}_{filename}"

        return base_dir / unique_filename

    async def save_schedule(self, schedule: ScheduleModel) -> models.Schedule:
        """Save schedule to database, updating if it already exists"""
        # Pad schedule unique_id to 8 digits
        padded_id = schedule.unique_id.zfill(8)
        db_schedule = await self.get_schedule_by_unique_id(padded_id, schedule.nickname)

        if db_schedule is None:
            db_schedule = self._create_schedule(schedule)
            self.session.add(db_schedule)
        else:
            # Clear existing days before updating
            db_schedule.days = []
            await self._update_schedule(db_schedule, schedule)

        await self.session.commit()
        # Refresh the session to ensure we have the latest data
        await self.session.refresh(db_schedule)
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
        for announcement_id in (new_ids - db_ids):
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
                    old_type=None
                )
            )
        
        # Removed announcements
        for announcement_id in (db_ids - new_ids):
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
                    new_type=None
                )
            )
        
        return changes

    async def get_changes(self, schedule: ScheduleModel) -> ScheduleChanges:
        """Compare schedule with database version and return changes"""
        padded_id = schedule.unique_id.zfill(8)
        db_schedule = await self.get_schedule_by_unique_id(padded_id, schedule.nickname)
        
        changes = ScheduleChanges(
            schedule_id=schedule.unique_id,
            structure_changed=False,
            days=[]
        )
        
        if not db_schedule:
            return changes

        # Compare each day
        for new_day in schedule.days:
            db_day = next(
                (d for d in db_schedule.days if d.unique_id == new_day.unique_id),
                None
            )
            if not db_day:
                continue

            day_changes = DayChanges(
                day_id=new_day.unique_id,
                lessons=[],
                homework=[],
                announcements=[]
            )

            # Create a map to track changes by lesson_id
            lesson_changes_map = {}

            # Check lesson order first
            if self._check_lesson_order(new_day.lessons, db_day.lessons):
                order_change = LessonChange(
                    lesson_id=new_day.unique_id,
                    order_changed=True
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
                        lesson_changes_map[lesson_id] = LessonChange(lesson_id=lesson_id)
                    
                    change = lesson_changes_map[lesson_id]
                    
                    # Check mark changes
                    if new_lesson.mark != db_lesson.mark and (new_lesson.mark is not None or db_lesson.mark is not None):
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

            if day_changes.lessons or day_changes.homework or day_changes.announcements:
                changes.days.append(day_changes)

        return changes

    def _create_schedule(self, schedule: ScheduleModel) -> models.Schedule:
        """Create new schedule in database"""
        unique_id = schedule.unique_id.zfill(8)
        db_schedule = models.Schedule(unique_id=unique_id, nickname=schedule.nickname)

        for day in schedule.days:
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
        """Update existing schedule with new data"""
        db_schedule.nickname = schedule.nickname

        # Create new days
        for day in schedule.days:
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

    async def _update_day(self, db_day: models.SchoolDay, day: SchoolDay):
        """Update existing day with new data"""
        # Track existing items by index instead of subject
        existing_lessons = {l.index: l for l in db_day.lessons}
        existing_announcements = {a.unique_id: a for a in db_day.announcements}

        # Update lessons
        new_lessons = []
        for lesson in day.lessons:
            if lesson.index in existing_lessons:
                db_lesson = existing_lessons[lesson.index]
                self._update_lesson(db_lesson, lesson)
                new_lessons.append(db_lesson)
            else:
                db_lesson = self._create_lesson(lesson)
                db_lesson.day = db_day
                new_lessons.append(db_lesson)

        db_day.lessons = new_lessons

        # Update announcements
        new_announcements = []
        for announcement in day.announcements:
            if announcement.unique_id in existing_announcements:
                db_announcement = existing_announcements[announcement.unique_id]
                self._update_announcement(db_announcement, announcement)
                new_announcements.append(db_announcement)
            else:
                db_announcement = self._create_announcement(announcement)
                db_announcement.day = db_day
                new_announcements.append(db_announcement)

        db_day.announcements = new_announcements

    def _update_lesson(self, db_lesson: models.Lesson, lesson: Lesson):
        """Update existing lesson with new data"""
        db_lesson.index = lesson.index
        db_lesson.subject = lesson.subject
        db_lesson.room = lesson.room
        db_lesson.topic = lesson.topic
        db_lesson.mark = lesson.mark

        if lesson.homework:
            if db_lesson.homework:
                self._update_homework(db_lesson.homework, lesson.homework)
            else:
                db_lesson.homework = self._create_homework(lesson.homework)
        elif db_lesson.homework:
            db_lesson.homework = None

    def _update_homework(self, db_homework: models.Homework, homework: Homework):
        """Update existing homework with new data"""
        db_homework.text = homework.text

        # Update links
        existing_links = {l.unique_id: l for l in db_homework.links}
        new_links = []
        for link in homework.links:
            if link.unique_id in existing_links:
                db_link = existing_links[link.unique_id]
                db_link.original_url = link.original_url
                db_link.destination_url = link.destination_url
                new_links.append(db_link)
            else:
                new_links.append(self._create_link(link))
        db_homework.links = new_links

        # Update attachments
        existing_attachments = {a.unique_id: a for a in db_homework.attachments}
        new_attachments = []
        for attachment in homework.attachments:
            if attachment.unique_id in existing_attachments:
                db_attachment = existing_attachments[attachment.unique_id]
                db_attachment.filename = attachment.filename
                db_attachment.url = attachment.url
                new_attachments.append(db_attachment)
            else:
                new_attachments.append(self._create_attachment(attachment))
        db_homework.attachments = new_attachments

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

        if lesson.homework:
            db_lesson.homework = self._create_homework(lesson.homework)

        return db_lesson

    def _create_homework(self, homework: Homework) -> models.Homework:
        """Create homework with all its data"""
        db_homework = models.Homework(unique_id=homework.unique_id, text=homework.text)

        for link in homework.links:
            db_homework.links.append(self._create_link(link))

        for attachment in homework.attachments:
            db_homework.attachments.append(self._create_attachment(attachment))

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
        return models.Announcement(
            unique_id=announcement.unique_id,
            type=announcement.type.value,  # Store the enum value, not the enum itself
            text=announcement.text,
            behavior_type=announcement.behavior_type,
            description=announcement.description,
            rating=announcement.rating,
            subject=announcement.subject,
        )
