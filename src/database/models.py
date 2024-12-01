from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy import String
from sqlalchemy import Enum as SQLAEnum
from sqlalchemy import ForeignKey, Index
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    validates,
)

# Define AnnouncementType directly here instead of importing from schema
from enum import Enum


class AnnouncementType(str, Enum):
    BEHAVIOR = "behavior"
    GENERAL = "general"


if TYPE_CHECKING:
    from .models import (
        Announcement,
        Attachment,
        Homework,
        Lesson,
        Link,
        Schedule,
        SchoolDay,
    )


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models"""

    pass


class Schedule(Base):
    """
    Represents a school schedule for a specific time period.

    Attributes:
        id: Primary key in YYYYWW format
        nickname: Identifier for which student this schedule belongs to
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
        days: List of school days in this schedule
        attachments: List of attachments for the entire schedule
    """

    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(6), primary_key=True)  # YYYYWW format
    nickname: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    days: Mapped[list[SchoolDay]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )
    attachments: Mapped[list[Attachment]] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
        primaryjoin="and_(Schedule.id==Attachment.schedule_id, "
        "Attachment.homework_id.is_(None), "
        "Attachment.lesson_id.is_(None))",
    )

    __table_args__ = (Index("ix_schedules_nickname_id", "nickname", "id", unique=True),)

    @validates("id")
    def validate_id(self, key: str, value: str) -> str:
        """Validate id is in YYYYWW format"""
        if not value or len(value) != 6 or not value.isdigit():
            raise ValueError("id must be a 6-digit string in YYYYWW format")
        return value

    @validates("nickname")
    def validate_nickname(self, key: str, value: str) -> str:
        """Validate nickname is not empty"""
        if not value or not value.strip():
            raise ValueError("nickname cannot be empty")
        return value.strip()


class SchoolDay(Base):
    __tablename__ = "school_days"

    id: Mapped[str] = mapped_column(String(8), primary_key=True)  # YYYYMMDD format
    date: Mapped[datetime] = mapped_column(nullable=False)
    schedule_id: Mapped[str] = mapped_column(ForeignKey("schedules.id"))

    schedule: Mapped[Schedule] = relationship(back_populates="days")
    lessons: Mapped[list[Lesson]] = relationship(
        back_populates="day", cascade="all, delete-orphan"
    )
    announcements: Mapped[list[Announcement]] = relationship(
        back_populates="day", cascade="all, delete-orphan"
    )

    @validates("id")
    def validate_id(self, key: str, value: str) -> str:
        """Validate id is in YYYYMMDD format"""
        if not value or len(value) != 8 or not value.isdigit():
            raise ValueError("id must be an 8-digit string in YYYYMMDD format")
        return value

    @validates("date")
    def validate_date(self, key: str, value: datetime) -> datetime:
        """Validate date is not None and is timezone-aware"""
        if value is None:
            raise ValueError("date cannot be None")
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # day_id_index format
    index: Mapped[int] = mapped_column()
    subject: Mapped[str] = mapped_column(String(255))
    room: Mapped[str | None] = mapped_column(String(50))
    topic: Mapped[str | None] = mapped_column(String)
    mark: Mapped[int | None] = mapped_column()
    day_id: Mapped[str] = mapped_column(ForeignKey("school_days.id"))

    day: Mapped[SchoolDay] = relationship(back_populates="lessons")
    homework: Mapped[Homework | None] = relationship(
        back_populates="lesson", cascade="all, delete-orphan", uselist=False
    )
    topic_attachments: Mapped[list[Attachment]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
        primaryjoin="and_(Lesson.id==Attachment.lesson_id, "
        "Attachment.homework_id.is_(None))",
    )

    @validates("id")
    def validate_id(self, key: str, value: str) -> str:
        """Validate id is in day_id_index format"""
        parts = value.split("_")
        if len(parts) != 3:  # Should be [YYYYMMDD, DD, index]
            raise ValueError("id must be in format scheduleid_DD_index")

        schedule_id, day, index = parts
        if len(schedule_id) != 8 or not schedule_id.isdigit():
            raise ValueError("Schedule part of id must be 8 digits (YYYYMMDD)")
        if len(day) != 2 or not day.isdigit():
            raise ValueError("Day part of id must be 2 digits")
        if not index.isdigit():
            raise ValueError("Index part must be a number")

        return value

    @validates("mark")
    def validate_mark(self, key: str, value: int | None) -> int | None:
        """Validate mark is between 1 and 10 or None"""
        if value is not None and (value < 1 or value > 10):
            raise ValueError("mark must be between 1 and 10")
        return value

    @validates("subject")
    def validate_subject(self, key: str, value: str) -> str:
        """Validate subject is not empty"""
        if not value or not value.strip():
            raise ValueError("subject cannot be empty")
        return value

    @validates("index")
    def validate_index(self, key: str, value: int) -> int:
        """Validate index is positive"""
        if value < 1:
            raise ValueError("index must be positive")
        return value

    def create_topic_attachment(self, filename: str, url: str) -> Attachment:
        """Helper method to create a topic attachment"""
        day_num = self.day.date.strftime("%d")
        attachment_id = f"{self.id}_{hashlib.md5(filename.encode()).hexdigest()[:6]}"

        attachment = Attachment(
            id=attachment_id, filename=filename, url=url, lesson=self
        )
        return attachment


class Homework(Base):
    __tablename__ = "homework"

    id: Mapped[str] = mapped_column(
        String(30), primary_key=True
    )  # lesson_id_hash format
    text: Mapped[str | None] = mapped_column(String)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"))

    lesson: Mapped[Lesson] = relationship(back_populates="homework")
    links: Mapped[list[Link]] = relationship(
        back_populates="homework", cascade="all, delete-orphan"
    )
    attachments: Mapped[list[Attachment]] = relationship(
        back_populates="homework", cascade="all, delete-orphan"
    )

    @validates("id")
    def validate_id(self, key: str, value: str) -> str:
        """Validate id is in lesson_id_hash format"""
        parts = value.split("_")
        if len(parts) != 4:  # Should be [YYYYMMDD, DD, index, hash]
            raise ValueError("id must be in format scheduleid_DD_index_hash")

        schedule_id, day, index, hash_part = parts
        if len(schedule_id) != 8 or not schedule_id.isdigit():
            raise ValueError("Schedule part of id must be 8 digits (YYYYMMDD)")
        if len(day) != 2 or not day.isdigit():
            raise ValueError("Day part of id must be 2 digits")
        if not index.isdigit():
            raise ValueError("Index part must be a number")

        return value


class Link(Base):
    __tablename__ = "links"

    id: Mapped[str] = mapped_column(
        String(40), primary_key=True
    )  # homework_id_hash format
    original_url: Mapped[str] = mapped_column(String(2048))
    destination_url: Mapped[str | None] = mapped_column(String(2048))
    homework_id: Mapped[str] = mapped_column(ForeignKey("homework.id"))

    homework: Mapped[Homework] = relationship(back_populates="links")

    @validates("id")
    def validate_id(self, key: str, value: str) -> str:
        """Validate id is in homework_id_hash format"""
        parts = value.split("_")
        if len(parts) != 5:  # Should be [YYYYMMDD, DD, index, homework_hash, link_hash]
            raise ValueError(
                "id must be in format scheduleid_DD_index_homeworkhash_linkhash"
            )
        return value

    @validates("original_url", "destination_url")
    def validate_url(self, key: str, value: str | None) -> str | None:
        """Validate URL format"""
        if value is None and key == "destination_url":
            return None
        if value.startswith(("http://", "https://")):
            # Validate as URL
            result = urlparse(value)
            if all([result.scheme, result.netloc]):
                return value
        elif value.startswith("/"):
            # Validate as path
            return value
        raise ValueError("Must be a valid URL or path starting with /")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(
        String(40), primary_key=True
    )  # parent_id_hash format
    filename: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(2048))
    homework_id: Mapped[str | None] = mapped_column(ForeignKey("homework.id"))
    lesson_id: Mapped[str | None] = mapped_column(ForeignKey("lessons.id"))
    schedule_id: Mapped[str | None] = mapped_column(ForeignKey("schedules.id"))

    homework: Mapped[Homework | None] = relationship(back_populates="attachments")
    lesson: Mapped[Lesson | None] = relationship(back_populates="topic_attachments")
    schedule: Mapped[Schedule | None] = relationship(back_populates="attachments")

    @validates("id")
    def validate_id(self, key: str, value: str) -> str:
        """Validate id format based on parent type"""
        parts = value.split("_")
        if len(parts) < 2:  # At minimum need parent_id and hash
            raise ValueError("id must be in format parent_id_hash")
        return value

    @validates("url")
    def validate_url(self, key: str, value: str) -> str:
        """Validate URL or path format"""
        if value.startswith(("http://", "https://")):
            # Validate as URL
            result = urlparse(value)
            if all([result.scheme, result.netloc]):
                return value
        elif value.startswith("/"):
            # Validate as path
            return value
        raise ValueError("Must be a valid URL or path starting with /")

    def get_file_path(self) -> Path:
        """Get the file path for this attachment"""
        # Split id into components (parent_id_hash)
        parts = self.id.split("_")
        schedule_id = parts[0]  # First part is always schedule id

        # Create base directory path
        base_dir = Path("data/attachments") / schedule_id

        try:
            base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Error creating directory {base_dir}: {e}")

        return base_dir / f"{self.id}_{self.filename}"


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[str] = mapped_column(
        String(30), primary_key=True
    )  # day_id_type_hash format
    type: Mapped[AnnouncementType] = mapped_column(SQLAEnum(AnnouncementType))
    text: Mapped[str | None] = mapped_column(String)
    behavior_type: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String)
    rating: Mapped[str | None] = mapped_column(String(50))
    subject: Mapped[str | None] = mapped_column(String(255))
    day_id: Mapped[str] = mapped_column(ForeignKey("school_days.id"))

    day: Mapped[SchoolDay] = relationship(back_populates="announcements")

    @validates("id")
    def validate_id(self, key: str, value: str) -> str:
        """Validate id is in day_id_type_hash format"""
        parts = value.split("_")
        if len(parts) != 4:  # Should be [YYYYMMDD, DD, type, hash]
            raise ValueError("id must be in format scheduleid_DD_type_hash")

        schedule_id, day, type_part, hash_part = parts
        if len(schedule_id) != 8 or not schedule_id.isdigit():
            raise ValueError("Schedule part of id must be 8 digits (YYYYMMDD)")
        if len(day) != 2 or not day.isdigit():
            raise ValueError("Day part of id must be 2 digits")
        if type_part not in [t.value for t in AnnouncementType]:
            raise ValueError(
                f"Type must be one of: {[t.value for t in AnnouncementType]}"
            )

        return value

    @validates("type")
    def validate_type(
        self, key: str, value: str | AnnouncementType
    ) -> AnnouncementType:
        """Validate announcement type"""
        if isinstance(value, AnnouncementType):
            return value
        try:
            return AnnouncementType(value.lower())
        except ValueError as err:
            raise ValueError("type must be either 'behavior' or 'general'") from err

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validate_required_fields()

    def validate_required_fields(self):
        """Validate required fields based on announcement type"""
        if self.type == AnnouncementType.BEHAVIOR:
            if not all(
                [self.behavior_type, self.description, self.rating, self.subject]
            ):
                raise ValueError(
                    "Behavior announcements require behavior_type, description, rating, and subject"
                )
        elif self.type == AnnouncementType.GENERAL:
            if not self.text:
                raise ValueError("General announcements require text")
