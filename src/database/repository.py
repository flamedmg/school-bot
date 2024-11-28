from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from pathlib import Path
from . import models
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
            await self._update_schedule(db_schedule, schedule)

        await self.session.commit()
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
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _check_lesson_order(
        self, new_lessons: List[Lesson], db_lessons: List[models.Lesson]
    ) -> bool:
        """Check if lesson order has changed"""

        # Create lists of (index, subject, room) tuples for comparison
        # This better represents the actual lesson structure
        def get_lesson_info(lesson):
            return (lesson.index, lesson.subject, lesson.room)

        new_lesson_info = [get_lesson_info(l) for l in new_lessons]
        db_lesson_info = [get_lesson_info(l) for l in db_lessons]

        # Filter out group-specific lessons to avoid false positives
        def is_group_specific(lesson_info):
            return "(F)" in lesson_info[1] or "Balagurchiki" in lesson_info[1]

        new_lesson_info = [l for l in new_lesson_info if not is_group_specific(l)]
        db_lesson_info = [l for l in db_lesson_info if not is_group_specific(l)]

        # Compare the filtered lesson sequences
        return new_lesson_info != db_lesson_info

    def _check_lesson_marks(
        self, new_lessons: List[Lesson], db_lessons: List[models.Lesson]
    ) -> List[Dict[str, Any]]:
        """Check for changes in lesson marks"""
        changes = []
        db_lessons_dict = {l.unique_id: l for l in db_lessons}

        for new_lesson in new_lessons:
            if new_lesson.unique_id in db_lessons_dict:
                db_lesson = db_lessons_dict[new_lesson.unique_id]
                if new_lesson.mark != db_lesson.mark:
                    changes.append(
                        {
                            "lesson_id": new_lesson.unique_id,
                            "old": db_lesson.mark,
                            "new": new_lesson.mark,
                        }
                    )
        return changes

    def _get_lesson_key(self, lesson: Any) -> Tuple[int, str]:
        """Get a unique key for a lesson based on its index and room"""
        return (lesson.index, lesson.room)

    def _check_lesson_subjects(
        self, new_lessons: List[Lesson], db_lessons: List[models.Lesson]
    ) -> List[Dict[str, Any]]:
        """Check for changes in lesson subjects"""
        changes = []

        # Create dictionaries using lesson index and room as key
        db_lessons_dict = {self._get_lesson_key(l): l for l in db_lessons}

        for new_lesson in new_lessons:
            key = self._get_lesson_key(new_lesson)
            if key in db_lessons_dict:
                db_lesson = db_lessons_dict[key]
                # Only consider it a change if both subject and room are different
                # This helps avoid false positives with group-specific lessons
                if new_lesson.subject != db_lesson.subject and not (
                    ("(F)" in new_lesson.subject and "(F)" in db_lesson.subject)
                    or ("Balagurchiki" in (new_lesson.subject, db_lesson.subject))
                ):
                    changes.append(
                        {
                            "lesson_id": new_lesson.unique_id,
                            "old": db_lesson.subject,
                            "new": new_lesson.subject,
                        }
                    )
        return changes

    def _check_announcements(
        self,
        new_announcements: List[Announcement],
        db_announcements: List[models.Announcement],
    ) -> Dict[str, List[str]]:
        """Check for changes in announcements"""
        new_ids = {a.unique_id for a in new_announcements}
        db_ids = {a.unique_id for a in db_announcements}
        return {"added": list(new_ids - db_ids), "removed": list(db_ids - new_ids)}

    async def get_changes(self, schedule: ScheduleModel) -> Dict[str, Any]:
        """Compare schedule with database version and return changes"""
        padded_id = schedule.unique_id.zfill(8)
        db_schedule = await self.get_schedule_by_unique_id(padded_id, schedule.nickname)
        if not db_schedule:
            return {
                "lessons_changed": False,
                "marks": [],
                "subjects": [],
                "announcements": {"added": [], "removed": []},
            }

        changes = {
            "lessons_changed": False,
            "marks": [],
            "subjects": [],
            "announcements": {"added": [], "removed": []},
        }

        for day in schedule.days:
            db_day = next(
                (d for d in db_schedule.days if d.unique_id == day.unique_id), None
            )
            if not db_day:
                continue

            if self._check_lesson_order(day.lessons, db_day.lessons):
                changes["lessons_changed"] = True
                continue

            changes["marks"].extend(
                self._check_lesson_marks(day.lessons, db_day.lessons)
            )
            changes["subjects"].extend(
                self._check_lesson_subjects(day.lessons, db_day.lessons)
            )

            announcement_changes = self._check_announcements(
                day.announcements, db_day.announcements
            )
            changes["announcements"]["added"].extend(announcement_changes["added"])
            changes["announcements"]["removed"].extend(announcement_changes["removed"])

        return changes

    def _create_schedule(self, schedule: ScheduleModel) -> models.Schedule:
        """Create new schedule in database"""
        unique_id = schedule.unique_id.zfill(8)
        db_schedule = models.Schedule(unique_id=unique_id, nickname=schedule.nickname)

        for day in schedule.days:
            db_day = self._create_day(day)
            db_day.schedule = db_schedule
            db_schedule.days.append(db_day)

        return db_schedule

    async def _update_schedule(
        self, db_schedule: models.Schedule, schedule: ScheduleModel
    ):
        """Update existing schedule with new data"""
        db_schedule.nickname = schedule.nickname

        # Track existing days for efficient updates
        existing_days = {day.unique_id: day for day in db_schedule.days}
        new_days = {day.unique_id: day for day in schedule.days}

        # Update or create days
        for day_id, day in new_days.items():
            if day_id in existing_days:
                await self._update_day(existing_days[day_id], day)
            else:
                db_day = self._create_day(day)
                db_day.schedule = db_schedule
                db_schedule.days.append(db_day)

        # Remove days that no longer exist
        for day_id, db_day in existing_days.items():
            if day_id not in new_days:
                db_schedule.days.remove(db_day)

    async def _update_day(self, db_day: models.SchoolDay, day: SchoolDay):
        """Update existing day with new data"""
        # Track existing items
        existing_lessons = {l.unique_id: l for l in db_day.lessons}
        existing_announcements = {a.unique_id: a for a in db_day.announcements}

        # Update lessons
        new_lessons = []
        for lesson in day.lessons:
            if lesson.unique_id in existing_lessons:
                db_lesson = existing_lessons[lesson.unique_id]
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
        db_announcement.type = announcement.type.value.upper()
        db_announcement.text = announcement.text
        db_announcement.behavior_type = announcement.behavior_type
        db_announcement.description = announcement.description
        db_announcement.rating = announcement.rating
        db_announcement.subject = announcement.subject

    def _create_announcement(self, announcement: Announcement) -> models.Announcement:
        """Create an announcement with all its data"""
        return models.Announcement(
            unique_id=announcement.unique_id,
            type=announcement.type.value.upper(),
            text=announcement.text,
            behavior_type=announcement.behavior_type,
            description=announcement.description,
            rating=announcement.rating,
            subject=announcement.subject,
        )
