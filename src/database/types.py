from typing import List, Optional
from dataclasses import dataclass
from src.schedule.schema import AnnouncementType
from .enums import ChangeType


@dataclass
class LessonChange:
    """Represents changes in a lesson's core attributes"""

    lesson_id: str
    order_changed: bool = False
    mark_changed: bool = False
    old_mark: Optional[int] = None
    new_mark: Optional[int] = None
    subject_changed: bool = False
    old_subject: Optional[str] = None
    new_subject: Optional[str] = None


@dataclass
class HomeworkChange:
    """Represents changes in homework content"""

    lesson_id: str
    text_changed: bool = False
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    links_changed: bool = False
    attachments_changed: bool = False


@dataclass
class AnnouncementChange:
    """Represents changes in an announcement"""

    announcement_id: str
    type: ChangeType
    old_type: Optional[AnnouncementType] = None
    new_type: Optional[AnnouncementType] = None
    old_text: Optional[str] = None
    new_text: Optional[str] = None


@dataclass
class DayChanges:
    """Represents all changes within a school day"""

    day_id: str
    lessons: List[LessonChange]
    homework: List[HomeworkChange]
    announcements: List[AnnouncementChange]


@dataclass
class ScheduleChanges:
    """Represents all changes in a schedule"""

    schedule_id: str
    structure_changed: bool  # True if days were added/removed or their order changed
    days: List[DayChanges]

    def has_changes(self) -> bool:
        """Determine if there are any changes in the schedule."""
        if self.structure_changed:
            return True
        if self.days:
            return True
        return False
