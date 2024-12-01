from dataclasses import dataclass

from .enums import ChangeType
from .models import AnnouncementType


@dataclass
class LessonChange:
    """Represents changes in a lesson's core attributes"""

    lesson_id: str
    order_changed: bool = False
    mark_changed: bool = False
    old_mark: int | None = None
    new_mark: int | None = None
    subject_changed: bool = False
    old_subject: str | None = None
    new_subject: str | None = None


@dataclass
class HomeworkChange:
    """Represents changes in homework content"""

    lesson_id: str
    text_changed: bool = False
    old_text: str | None = None
    new_text: str | None = None
    links_changed: bool = False
    attachments_changed: bool = False


@dataclass
class AnnouncementChange:
    """Represents changes in an announcement"""

    announcement_id: str
    type: ChangeType
    old_type: AnnouncementType | None = None
    new_type: AnnouncementType | None = None
    old_text: str | None = None
    new_text: str | None = None


@dataclass
class DayChanges:
    """Represents all changes within a school day"""

    day_id: str
    lessons: list[LessonChange]
    homework: list[HomeworkChange]
    announcements: list[AnnouncementChange]


@dataclass
class ScheduleChanges:
    """Represents all changes in a schedule"""

    schedule_id: str
    structure_changed: bool  # True if days were added/removed or their order changed
    days: list[DayChanges]

    def has_changes(self) -> bool:
        """Determine if there are any changes in the schedule."""
        if self.structure_changed:
            return True
        if self.days:
            return True
        return False
