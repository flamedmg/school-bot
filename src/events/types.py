from datetime import datetime
from src.database.enums import ChangeType
from typing import List, Optional
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    HttpUrl,
    constr,
    NonNegativeInt,
)


class MarkChange(BaseModel):
    """Represents a change in a mark"""

    lesson_id: constr(min_length=1)
    old_mark: Optional[PositiveInt] = None
    new_mark: Optional[PositiveInt] = None
    change_type: ChangeType
    subject: constr(min_length=1)
    lesson_index: PositiveInt


class SubjectChange(BaseModel):
    """Represents a change in subject name"""

    lesson_id: constr(min_length=1)
    old_subject: constr(min_length=1)
    new_subject: constr(min_length=1)
    lesson_index: PositiveInt


class AnnouncementChange(BaseModel):
    """Represents a change in announcements"""

    announcement_id: constr(min_length=1)
    change_type: ChangeType
    text: Optional[str] = None


class ScheduleChanges(BaseModel):
    """All changes that might need user notification"""

    lessons_order_changed: bool
    marks: List[MarkChange] = []
    subjects: List[SubjectChange] = []
    announcements: List[AnnouncementChange] = []


class Student(BaseModel):
    """Student information model"""

    nickname: constr(min_length=1)
    username: constr(min_length=1)
    password: constr(min_length=1)
    emoji: constr(min_length=1, max_length=2) = "👤"


class CrawlEvent(BaseModel):
    """Event emitted to trigger schedule crawling"""

    timestamp: datetime
    student: Student


class MarkEvent(BaseModel):
    """Event emitted when a new mark is detected"""

    student_nickname: constr(min_length=1)
    subject: constr(min_length=1)
    new: constr(min_length=1)
    lesson_id: constr(min_length=1)


class AnnouncementEvent(BaseModel):
    """Event emitted when a new announcement is detected"""

    student_nickname: constr(min_length=1)
    text: constr(min_length=1)
    type: constr(min_length=1) = "general"
    behavior_type: Optional[constr(min_length=1)] = None
    description: Optional[constr(min_length=1)] = None
    rating: Optional[constr(min_length=1)] = None
    subject: Optional[constr(min_length=1)] = None


class AttachmentEvent(BaseModel):
    """Event emitted when a new attachment is detected"""

    student_nickname: constr(min_length=1)
    filename: constr(min_length=1)
    url: HttpUrl
    cookies: dict[str, str]
    unique_id: constr(min_length=1)  # Combined ID from schedule_id, subject, lesson_number, day_id


class TelegramMessageEvent(BaseModel):
    """Event emitted when a Telegram message is received"""

    message_id: NonNegativeInt
    chat_id: int
    text: constr(min_length=1)
    date: datetime


class TelegramCommandEvent(BaseModel):
    """Event emitted when a Telegram command is received"""

    command: constr(min_length=1)
    args: List[str] = []
    chat_id: int
    message_id: NonNegativeInt
    date: datetime


# Grade-related constants
GRADE_EMOJIS = {
    1: "💩",  # Total disaster, comrade
    2: "🪰",  # Like annoying fly in soup
    3: "🗑️",  # To gulag with this grade
    4: "🥔",  # Potato - basic survival, comrade!
    5: "⚒️",  # Hammer and sickle - working on it!
    6: "🚜",  # Tractor - making progress like a Kolkhoz!
    7: "🎭",  # Theater mask - Bolshoi level!
    8: "🚀",  # Sputnik - cosmic achievement!
    9: "🐻",  # Russian bear - powerful performance!
    10: "⭐️",  # Red star - supreme Soviet excellence!
}

GRADE_MESSAGES = {
    1: "Катастрофа, товарищ!",
    2: "Как муха в супе...",
    3: "Прямой путь в ГУЛАГ",
    4: "От картошки к звездам!",
    5: "Труд крепкий!",
    6: "Вперед к победе!",
    7: "Культурная революция!",
    8: "Космический успех!",
    9: "Могучий результат!",
    10: "Высшее достижение товарища!",
}
