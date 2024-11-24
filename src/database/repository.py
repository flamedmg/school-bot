from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import select
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
    def __init__(self, session: Session):
        self.session = session

    def save_schedule(self, schedule: ScheduleModel) -> models.Schedule:
        """Save schedule to database, updating if it already exists"""
        # Pad schedule unique_id to 8 digits
        padded_id = schedule.unique_id.zfill(8)
        db_schedule = self.get_schedule_by_unique_id(padded_id, schedule.nickname)

        if db_schedule is None:
            db_schedule = self._create_schedule(schedule)
            self.session.add(db_schedule)
        else:
            self._update_schedule(db_schedule, schedule)

        self.session.commit()
        return db_schedule

    def get_schedule_by_unique_id(
        self, unique_id: str, nickname: str
    ) -> Optional[models.Schedule]:
        """Get schedule by its unique ID and nickname"""
        # Ensure unique_id is padded to 8 digits
        padded_id = unique_id.zfill(8)
        return self.session.scalar(
            select(models.Schedule).where(
                models.Schedule.unique_id == padded_id,
                models.Schedule.nickname == nickname,
            )
        )

    def _check_lesson_order(
        self, new_lessons: List[Lesson], db_lessons: List[models.Lesson]
    ) -> bool:
        """Check if lesson order has changed"""
        # Ensure all lessons have proper parent references
        new_ids = []
        for lesson in new_lessons:
            if not lesson._day:
                raise ValueError("Lesson must be associated with a day")
            new_ids.append(lesson.unique_id)

        db_ids = [l.unique_id for l in db_lessons]
        return new_ids != db_ids

    def _check_lesson_marks(
        self, new_lessons: List[Lesson], db_lessons: List[models.Lesson]
    ) -> List[Dict[str, Any]]:
        """Check for changes in lesson marks"""
        changes = []
        db_lessons_dict = {l.unique_id: l for l in db_lessons}

        for new_lesson in new_lessons:
            if not new_lesson._day:
                raise ValueError("Lesson must be associated with a day")
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

    def _check_lesson_subjects(
        self, new_lessons: List[Lesson], db_lessons: List[models.Lesson]
    ) -> List[Dict[str, Any]]:
        """Check for changes in lesson subjects"""
        changes = []
        db_lessons_dict = {l.unique_id: l for l in db_lessons}

        for new_lesson in new_lessons:
            if not new_lesson._day:
                raise ValueError("Lesson must be associated with a day")
            if new_lesson.unique_id in db_lessons_dict:
                db_lesson = db_lessons_dict[new_lesson.unique_id]
                if new_lesson.subject != db_lesson.subject:
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
        # Ensure all announcements have proper parent references
        new_ids = set()
        for announcement in new_announcements:
            if not announcement._day:
                raise ValueError("Announcement must be associated with a day")
            new_ids.add(announcement.unique_id)

        db_ids = {a.unique_id for a in db_announcements}

        return {"added": list(new_ids - db_ids), "removed": list(db_ids - new_ids)}

    def get_changes(self, schedule: ScheduleModel) -> Dict[str, Any]:
        """Compare schedule with database version and return changes"""
        # Pad schedule unique_id to 8 digits
        padded_id = schedule.unique_id.zfill(8)
        db_schedule = self.get_schedule_by_unique_id(padded_id, schedule.nickname)
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

            # First check if lesson order/structure has changed
            if self._check_lesson_order(day.lessons, db_day.lessons):
                changes["lessons_changed"] = True
                continue

            # If lesson structure hasn't changed, check for specific changes
            changes["marks"].extend(
                self._check_lesson_marks(day.lessons, db_day.lessons)
            )
            changes["subjects"].extend(
                self._check_lesson_subjects(day.lessons, db_day.lessons)
            )

            # Check announcements
            announcement_changes = self._check_announcements(
                day.announcements, db_day.announcements
            )
            changes["announcements"]["added"].extend(announcement_changes["added"])
            changes["announcements"]["removed"].extend(announcement_changes["removed"])

        return changes

    def _create_schedule(self, schedule: ScheduleModel) -> models.Schedule:
        """Create new schedule in database"""
        # Pad week number with leading zero if needed
        unique_id = schedule.unique_id.zfill(8)
        db_schedule = models.Schedule(unique_id=unique_id, nickname=schedule.nickname)
        self.session.add(db_schedule)
        self.session.flush()  # Flush to get the id

        # Process each day
        for day in schedule.days:
            db_day = self._create_day(day)
            db_day.schedule_id = db_schedule.id  # Set the schedule relationship
            db_schedule.days.append(db_day)

        return db_schedule

    def _update_schedule(self, db_schedule: models.Schedule, schedule: ScheduleModel):
        """Update existing schedule with new data"""
        # Update nickname if changed
        db_schedule.nickname = schedule.nickname

        # Keep track of existing days by unique_id
        existing_days = {day.unique_id: day for day in db_schedule.days}

        # Reset days to maintain order
        db_schedule.days = []

        # Process each day
        for day in schedule.days:
            if day.unique_id in existing_days:
                db_day = self._update_day(existing_days[day.unique_id], day)
            else:
                db_day = self._create_day(day)
                db_day.schedule_id = db_schedule.id
            db_schedule.days.append(db_day)

    def _update_day(self, db_day: models.SchoolDay, day: SchoolDay) -> models.SchoolDay:
        """Update existing day with new data"""
        # Reset lists to maintain order
        db_day.lessons = []
        db_day.announcements = []

        # Process lessons and announcements
        self._process_lessons(db_day, day)
        self._process_announcements(db_day, day)

        return db_day

    def _create_day(self, day: SchoolDay) -> models.SchoolDay:
        """Create new day with all its data"""
        unique_id = day.date.strftime("%Y%m%d")
        db_day = models.SchoolDay(unique_id=unique_id, date=day.date)

        # Process lessons and announcements
        self._process_lessons(db_day, day)
        self._process_announcements(db_day, day)

        return db_day

    def _process_lessons(self, db_day: models.SchoolDay, day: SchoolDay):
        """Process all lessons for a day"""
        for lesson in day.lessons:
            # Set day reference before accessing unique_id
            lesson._day = day
            db_lesson = self._create_lesson(lesson)
            db_lesson.day_id = db_day.id
            db_day.lessons.append(db_lesson)

    def _create_lesson(self, lesson: Lesson) -> models.Lesson:
        """Create a lesson with all its data"""
        if not lesson._day:
            raise ValueError("Lesson must be associated with a day")

        db_lesson = models.Lesson(
            unique_id=lesson.unique_id,
            index=lesson.index,
            subject=lesson.subject,
            room=lesson.room,
            topic=lesson.topic,
            mark=lesson.mark,
        )

        if lesson.homework:
            lesson.homework._day = lesson._day
            homework = self._create_homework(lesson.homework)
            db_lesson.homework = homework

        return db_lesson

    def _create_homework(self, homework: Homework) -> models.Homework:
        """Create homework with all its data"""
        db_homework = models.Homework(unique_id=homework.unique_id, text=homework.text)

        # Process links
        for link in homework.links:
            link._day = homework._day
            db_link = self._create_link(link)
            db_homework.links.append(db_link)

        # Process attachments
        for attachment in homework.attachments:
            attachment._day = homework._day
            db_attachment = self._create_attachment(attachment)
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

    def _process_announcements(self, db_day: models.SchoolDay, day: SchoolDay):
        """Process all announcements for a day"""
        for announcement in day.announcements:
            # Set day reference before accessing unique_id
            announcement._day = day
            db_announcement = self._create_announcement(announcement)
            db_announcement.day_id = db_day.id
            db_day.announcements.append(db_announcement)

    def _create_announcement(self, announcement: Announcement) -> models.Announcement:
        """Create an announcement with all its data"""
        if not announcement._day:
            raise ValueError("Announcement must be associated with a day")

        return models.Announcement(
            unique_id=announcement.unique_id,
            type=announcement.type.value.upper(),
            text=announcement.text,
            behavior_type=announcement.behavior_type,
            description=announcement.description,
            rating=announcement.rating,
            subject=announcement.subject,
        )
