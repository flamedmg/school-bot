from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, validator, model_validator
import hashlib

# Data Models
class AnnouncementType(str, Enum):
    BEHAVIOR = "behavior"
    GENERAL = "general"

class Attachment(BaseModel):
    filename: str
    url: str
    _day: Optional['SchoolDay'] = None  # Add day reference

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on day and content"""
        content = f"{self.filename}:{self.url}"
        content_hash = hashlib.md5(content.encode()).hexdigest()[:6]
        day_prefix = self._day.unique_id if self._day else "00000000"
        return f"{day_prefix}_{content_hash}"

class Link(BaseModel):
    original_url: str
    destination_url: Optional[str] = None
    _day: Optional['SchoolDay'] = None  # Add day reference

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on day and URLs"""
        content = f"{self.original_url}:{self.destination_url or ''}"
        content_hash = hashlib.md5(content.encode()).hexdigest()[:6]
        day_prefix = self._day.unique_id if self._day else "00000000"
        return f"{day_prefix}_{content_hash}"

class Homework(BaseModel):
    text: Optional[str] = None
    links: List[Link] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)
    _day: Optional['SchoolDay'] = None  # Add day reference

    def __init__(self, **data):
        super().__init__(**data)
        # Set day reference for nested objects
        for link in self.links:
            link._day = self._day
        for attachment in self.attachments:
            attachment._day = self._day

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on day and content"""
        content = f"{self.text or ''}:{[link.unique_id for link in self.links]}:{[att.unique_id for att in self.attachments]}"
        content_hash = hashlib.md5(content.encode()).hexdigest()[:6]
        day_prefix = self._day.unique_id if self._day else "00000000"
        return f"{day_prefix}_{content_hash}"

class Lesson(BaseModel):
    index: int
    subject: str
    room: Optional[str] = None
    topic: Optional[str] = None
    homework: Optional[Homework] = None
    mark: Optional[int] = None
    _day: Optional['SchoolDay'] = None

    def __init__(self, **data):
        super().__init__(**data)
        # Set day reference for homework if present
        if self.homework:
            self.homework._day = self._day

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
        """Validate announcement fields after model creation"""
        if self.type == AnnouncementType.BEHAVIOR:
            missing_fields = []
            if not self.behavior_type:
                missing_fields.append("behavior_type")
            if not self.description:
                missing_fields.append("description")
            if not self.rating:
                missing_fields.append("rating")
            if not self.subject:
                missing_fields.append("subject")
            
            if missing_fields:
                raise ValueError(
                    f"Behavior announcement requires: {', '.join(missing_fields)}"
                )
        elif self.type == AnnouncementType.GENERAL and not self.text:
            raise ValueError("General announcement requires text")
        return self

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on day and type"""
        if not self._day:
            raise ValueError("Announcement must be associated with a day")
        content_hash = hashlib.md5(
            (self.text or f"{self.behavior_type}{self.subject}{self.rating}").encode()
        ).hexdigest()[:6]
        return f"{self._day.unique_id}_{self.type[0]}{content_hash}"

class SchoolDay(BaseModel):
    date: datetime
    lessons: List[Lesson] = Field(default_factory=list)
    announcements: List[Announcement] = Field(default_factory=list)

    def __init__(self, **data):
        """
        Initialize a SchoolDay instance.
        
        Args:
            **data: Dictionary of attributes to set on the instance
            
        Sets parent references for all nested objects (lessons, homework, etc.)
        """
        super().__init__(**data)
        self._set_parent_references()

    def _set_parent_references(self) -> None:
        """
        Set parent references for all nested objects.
        
        This ensures all child objects (lessons, homework, attachments, etc.)
        have a reference back to their parent SchoolDay instance.
        """
        for lesson in self.lessons:
            lesson._day = self
            if lesson.homework:
                lesson.homework._day = self
                for link in lesson.homework.links:
                    link._day = self
                for attachment in lesson.homework.attachments:
                    attachment._day = self
        for announcement in self.announcements:
            announcement._day = self

    def append_lesson(self, lesson: Lesson):
        """Append lesson and set parent reference"""
        lesson._day = self
        if lesson.homework:
            lesson.homework._day = self
            for link in lesson.homework.links:
                link._day = self
            for attachment in lesson.homework.attachments:
                attachment._day = self
        self.lessons.append(lesson)

    def append_announcement(self, announcement: Announcement):
        """Append announcement and set parent reference"""
        announcement._day = self
        self.announcements.append(announcement)

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on date (YYYYMMDD format)"""
        return self.date.strftime("%Y%m%d")

class Schedule(BaseModel):
    days: List[SchoolDay]
    attachments: List[Attachment] = Field(default_factory=list)

    @validator('days')
    def validate_days(cls, v):
        if not v:
            raise ValueError("Schedule must have at least one day")
        return v

    @property
    def unique_id(self) -> str:
        """Generate unique ID based on first day (YYYYMMDD format)"""
        if not self.days:
            raise ValueError("Schedule must have at least one day")
        return self.days[0].date.strftime("%Y%m%d")

# Scraping Schema
schema = {
    "name": "Student Journal Lessons",
    "baseSelector": "div.student-journal-lessons-table-holder",
    "fields": [
        {
            "name": "days",
            "selector": "h2, table.lessons-table", 
            "type": "nested_list",
            "fields": [
                {
                    "name": "date",
                    "type": "text"
                },
                {
                    "name": "lessons",
                    "selector": "tbody tr:not(.info)",
                    "type": "nested_list",
                    "fields": [
                        {
                            "name": "number",
                            "selector": "span.number",
                            "type": "text"
                        },
                        {
                            "name": "subject",
                            "selector": "span.title",
                            "type": "text"
                        },
                        {
                            "name": "room",
                            "selector": "span.room",
                            "type": "text"
                        },
                        {
                            "name": "topic",
                            "selector": "td.subject p",
                            "type": "text"
                        },
                        {
                            "name": "homework",
                            "type": "nested",
                            "selector": "td.hometask",
                            "fields": [
                                {
                                    "name": "text",
                                    "selector": "span p",
                                    "type": "text"
                                },
                                {
                                    "name": "links",
                                    "selector": "a",
                                    "type": "list",
                                    "fields": [
                                        {
                                            "name": "url",
                                            "type": "attribute",
                                            "attribute": "href"
                                        }
                                    ]
                                },
                                {
                                    "name": "attachments",
                                    "selector": "a.file",
                                    "type": "list",
                                    "fields": [
                                        {
                                            "name": "filename",
                                            "type": "text"
                                        },
                                        {
                                            "name": "url",
                                            "type": "attribute",
                                            "attribute": "href"
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "name": "mark",
                            "selector": "td.score span.score",
                            "type": "list",
                            "fields": [
                                {
                                    "name": "score",
                                    "type": "text"
                                }
                            ]
                        }
                    ]
                },
                {
                    "name": "announcements",
                    "selector": "tr.info td.info-content p",
                    "type": "list",
                    "fields": [
                        {
                            "name": "text",
                            "type": "text"
                        },
                        {
                            "name": "date",
                            "type": "attribute",
                            "attribute": "title",
                            "selector": "tr.info td.info-content p"
                        }
                    ]
                },
            ]
        }
    ]
}
