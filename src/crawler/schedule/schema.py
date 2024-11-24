from datetime import datetime, date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, validator, model_validator
import hashlib

class AnnouncementType(str, Enum):
    BEHAVIOR = "behavior"
    GENERAL = "general"

class Attachment(BaseModel):
    filename: str
    url: str

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on filename and url"""
        content = f"{self.filename}:{self.url}"
        return hashlib.md5(content.encode()).hexdigest()

class Link(BaseModel):
    original_url: str
    destination_url: Optional[str] = None

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on URLs"""
        content = f"{self.original_url}:{self.destination_url or ''}"
        return hashlib.md5(content.encode()).hexdigest()

class Homework(BaseModel):
    text: Optional[str] = None
    links: List[Link] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on content"""
        content = f"{self.text or ''}:{[link.unique_id for link in self.links]}:{[att.unique_id for att in self.attachments]}"
        return hashlib.md5(content.encode()).hexdigest()

class Lesson(BaseModel):
    index: int
    subject: str
    room: Optional[str] = None
    topic: Optional[str] = None
    homework: Optional[Homework] = None
    mark: Optional[int] = None
    _day: Optional['SchoolDay'] = None

    @validator('subject')
    def validate_subject(cls, v):
        if not v or not v.strip():
            raise ValueError("Subject cannot be empty")
        return v.strip()

    @validator('mark')
    def validate_mark(cls, v):
        if v is not None and not (1 <= v <= 10):
            raise ValueError("Mark must be between 1 and 10")
        return v

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on day and index"""
        if not self._day:
            raise ValueError("Lesson must be associated with a day")
        return f"{self._day.unique_id}_{self.index}"

class Announcement(BaseModel):
    type: AnnouncementType
    text: Optional[str] = None
    behavior_type: Optional[str] = None  # For behavior announcements
    description: Optional[str] = None    # For behavior announcements
    rating: Optional[str] = None         # For behavior announcements
    subject: Optional[str] = None        # For behavior announcements
    _day: Optional['SchoolDay'] = None

    @model_validator(mode='after')
    def validate_announcement(self) -> 'Announcement':
        """Validate announcement fields based on type"""
        if self.type == AnnouncementType.BEHAVIOR:
            if not all([
                self.behavior_type,
                self.description,
                self.rating,
                self.subject
            ]):
                raise ValueError("Behavior announcement requires behavior_type, description, rating, and subject")
        elif self.type == AnnouncementType.GENERAL:
            if not self.text:
                raise ValueError("General announcement requires text")
        return self

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on day and content"""
        if not self._day:
            raise ValueError("Announcement must be associated with a day")
        content = f"{self.type}:{self.text or ''}:{self.behavior_type or ''}:{self.description or ''}"
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{self._day.unique_id}_{self.type}_{content_hash}"

class SchoolDay(BaseModel):
    date: datetime
    lessons: List[Lesson] = Field(default_factory=list)
    announcements: List[Announcement] = Field(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)
        # Set parent reference for lessons and announcements
        for lesson in self.lessons:
            lesson._day = self
        for announcement in self.announcements:
            announcement._day = self

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on date (YYYYMMDD format)"""
        return self.date.strftime("%Y%m%d")

class Schedule(BaseModel):
    nickname: str = Field(description="Identifier for which student this schedule belongs to")
    days: List[SchoolDay]
    attachments: List[Attachment] = Field(default_factory=list)

    @validator('days')
    def validate_days(cls, v):
        if not v:
            raise ValueError("Schedule must have at least one day")
        return v

    @validator('nickname')
    def validate_nickname(cls, v):
        if not v or not v.strip():
            raise ValueError("Nickname cannot be empty")
        return v.strip()

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on first day (YYYYWW format)"""
        if not self.days:
            raise ValueError("Schedule must have at least one day")
        first_day = self.days[0].date
        year = first_day.isocalendar()[0]
        week = first_day.isocalendar()[1]
        return f"{year}{week}"
