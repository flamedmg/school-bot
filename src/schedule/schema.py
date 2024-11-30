from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import hashlib


class AnnouncementType(str, Enum):
    BEHAVIOR = "behavior"
    GENERAL = "general"


class Attachment(BaseModel):
    filename: str
    url: str
    _day: Optional["SchoolDay"] = None

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on filename and url"""
        if not self._day:
            raise ValueError("Attachment must be associated with a day")
        content = f"{self.filename}:{self.url}"
        return f"{self._day.unique_id}_{hashlib.md5(content.encode()).hexdigest()[:6]}"


class Link(BaseModel):
    original_url: str
    destination_url: Optional[str] = None
    _day: Optional["SchoolDay"] = None

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on URLs"""
        if not self._day:
            raise ValueError("Link must be associated with a day")
        content = f"{self.original_url}:{self.destination_url or ''}"
        return f"{self._day.unique_id}_{hashlib.md5(content.encode()).hexdigest()[:6]}"


class Homework(BaseModel):
    text: Optional[str] = None
    links: List[Link] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)
    _day: Optional["SchoolDay"] = None

    def __init__(self, **data):
        super().__init__(**data)
        # Set parent reference for links and attachments
        for link in self.links:
            link._day = self._day
        for attachment in self.attachments:
            attachment._day = self._day

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on content"""
        if not self._day:
            raise ValueError("Homework must be associated with a day")
        content = f"{self.text or ''}:{[link.unique_id for link in self.links]}:{[att.unique_id for att in self.attachments]}"
        return f"{self._day.unique_id}_{hashlib.md5(content.encode()).hexdigest()[:6]}"


class Lesson(BaseModel):
    index: int
    subject: str
    room: Optional[str] = None
    topic: Optional[str] = None
    topic_attachments: List[Attachment] = Field(default_factory=list)
    homework: Optional[Homework] = None
    mark: Optional[int] = None
    _day: Optional["SchoolDay"] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.homework:
            self.homework._day = self._day
        for attachment in self.topic_attachments:
            attachment._day = self._day

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v):
        if not v or not v.strip():
            raise ValueError("Subject cannot be empty")
        return v.strip()

    @field_validator("mark")
    @classmethod
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
    description: Optional[str] = None  # For behavior announcements
    rating: Optional[str] = None  # For behavior announcements
    subject: Optional[str] = None  # For behavior announcements
    _day: Optional["SchoolDay"] = None

    @model_validator(mode="after")
    def validate_announcement(self) -> "Announcement":
        """Validate announcement fields based on type"""
        if self.type == AnnouncementType.BEHAVIOR:
            if not all(
                [self.behavior_type, self.description, self.rating, self.subject]
            ):
                raise ValueError(
                    "Behavior announcement requires behavior_type, description, rating, and subject"
                )
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
        content_hash = hashlib.md5(content.encode()).hexdigest()[:6]
        type_prefix = "b" if self.type == AnnouncementType.BEHAVIOR else "g"
        return f"{self._day.unique_id}_{type_prefix}{content_hash}"


class SchoolDay(BaseModel):
    date: datetime
    lessons: List[Lesson] = Field(default_factory=list)
    announcements: List[Announcement] = Field(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)
        # Set parent reference for lessons and announcements
        for lesson in self.lessons:
            lesson._day = self
            # Set parent reference for topic attachments
            for attachment in lesson.topic_attachments:
                attachment._day = self
            if lesson.homework:
                lesson.homework._day = self
                # Set parent reference for homework attachments and links
                for attachment in lesson.homework.attachments:
                    attachment._day = self
                for link in lesson.homework.links:
                    link._day = self
        for announcement in self.announcements:
            announcement._day = self

    def append_lesson(self, lesson: Lesson):
        """Add a lesson to the day"""
        lesson._day = self
        if lesson.homework:
            lesson.homework._day = self
            # Set parent reference for homework attachments and links
            for attachment in lesson.homework.attachments:
                attachment._day = self
            for link in lesson.homework.links:
                link._day = self
        self.lessons.append(lesson)

    def append_announcement(self, announcement: Announcement):
        """Add an announcement to the day"""
        announcement._day = self
        self.announcements.append(announcement)

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on date (YYYYMMDD format)"""
        return self.date.strftime("%Y%m%d")


class Schedule(BaseModel):
    nickname: str = Field(
        description="Identifier for which student this schedule belongs to"
    )
    days: List[SchoolDay]
    attachments: List[Attachment] = Field(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)
        # Set parent reference for schedule attachments
        for attachment in self.attachments:
            attachment._day = self.days[0] if self.days else None

    @field_validator("days")
    @classmethod
    def validate_days(cls, v):
        if not v:
            raise ValueError("Schedule must have at least one day")
        return v

    @field_validator("nickname")
    @classmethod
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
        return f"{year}{week:02d}"  # Year (4 digits) + Week (2 digits padded) = 6 characters
