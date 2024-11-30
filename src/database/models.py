from __future__ import annotations
from datetime import datetime, UTC
from typing import List, Optional, TYPE_CHECKING
from loguru import logger
from sqlalchemy import ForeignKey, String, DateTime, Enum as SQLAEnum, Index
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
    DeclarativeBase,
    validates,
)
from src.schedule.schema import AnnouncementType
from pathlib import Path

if TYPE_CHECKING:
    from .models import (
        Schedule,
        SchoolDay,
        Lesson,
        Homework,
        Link,
        Attachment,
        Announcement,
    )


class Base(DeclarativeBase):
    """Base class for all database models"""

    pass


class Schedule(Base):
    """
    Represents a school schedule for a specific time period.

    Attributes:
        id: Primary key
        unique_id: Unique identifier in YYYYWW format, padded to 8 digits
        nickname: Identifier for which student this schedule belongs to
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
        days: List of school days in this schedule
    """

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    unique_id: Mapped[str] = mapped_column(String(8))
    nickname: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    days: Mapped[List["SchoolDay"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_schedules_nickname_unique_id", "nickname", "unique_id", unique=True),
    )

    @validates("unique_id")
    def validate_unique_id(self, key: str, value: str) -> str:
        """Validate unique_id is an 8-digit string"""
        if not value or len(value) != 8 or not value.isdigit():
            raise ValueError("unique_id must be an 8-digit string")
        return value


class SchoolDay(Base):
    __tablename__ = "school_days"

    id: Mapped[int] = mapped_column(primary_key=True)
    unique_id: Mapped[str] = mapped_column(String(8))  # YYYYMMDD format
    date: Mapped[datetime] = mapped_column()
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id"))

    schedule: Mapped["Schedule"] = relationship(back_populates="days")
    lessons: Mapped[List["Lesson"]] = relationship(
        back_populates="day", cascade="all, delete-orphan"
    )
    announcements: Mapped[List["Announcement"]] = relationship(
        back_populates="day", cascade="all, delete-orphan"
    )

    @validates("unique_id")
    def validate_unique_id(self, key: str, value: str) -> str:
        """Validate unique_id is in YYYYMMDD format"""
        if not value or len(value) != 8 or not value.isdigit():
            raise ValueError("unique_id must be an 8-digit string in YYYYMMDD format")
        return value


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    unique_id: Mapped[str] = mapped_column(String(20))
    index: Mapped[int] = mapped_column()
    subject: Mapped[str] = mapped_column(String(255))
    room: Mapped[Optional[str]] = mapped_column(String(50))
    topic: Mapped[Optional[str]] = mapped_column(String)
    mark: Mapped[Optional[int]] = mapped_column()
    day_id: Mapped[int] = mapped_column(ForeignKey("school_days.id"))

    day: Mapped["SchoolDay"] = relationship(back_populates="lessons")
    homework: Mapped[Optional["Homework"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan", uselist=False
    )


class Homework(Base):
    __tablename__ = "homework"

    id: Mapped[int] = mapped_column(primary_key=True)
    unique_id: Mapped[str] = mapped_column(String(20))
    text: Mapped[Optional[str]] = mapped_column(String)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))

    lesson: Mapped["Lesson"] = relationship(back_populates="homework")
    links: Mapped[List["Link"]] = relationship(
        back_populates="homework", cascade="all, delete-orphan"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        back_populates="homework", cascade="all, delete-orphan"
    )


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True)
    unique_id: Mapped[str] = mapped_column(String(20))
    original_url: Mapped[str] = mapped_column(String(2048))
    destination_url: Mapped[Optional[str]] = mapped_column(String(2048))
    homework_id: Mapped[int] = mapped_column(ForeignKey("homework.id"))

    homework: Mapped["Homework"] = relationship(back_populates="links")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    unique_id: Mapped[str] = mapped_column(
        String(100)
    )  # Increased length for new format
    filename: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(2048))
    homework_id: Mapped[int] = mapped_column(ForeignKey("homework.id"))

    homework: Mapped["Homework"] = relationship(back_populates="attachments")

    def get_file_path(self) -> Path:
        """
        Get the file path for this attachment based on its unique_id.
        The unique_id format is: schedule_id_day_id_subject_lesson
        """
        # Split unique_id into components
        components = self.unique_id.split("_")
        if len(components) < 4:
            # Handle invalid unique_id format
            schedule_id = "unknown"
        else:
            schedule_id = components[0]

        # Create base directory path
        base_dir = Path("data/attachments") / schedule_id

        try:
            # Create directory and parents if they don't exist
            # exist_ok=True prevents errors if directory already exists
            base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            # Log error but continue - directory might already exist
            logger.warning(f"Error creating directory {base_dir}: {e}")

        # Create filename using the unique_id and original filename
        unique_filename = f"{self.unique_id}_{self.filename}"

        return base_dir / unique_filename


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(primary_key=True)
    unique_id: Mapped[str] = mapped_column(String(20))
    type: Mapped[AnnouncementType] = mapped_column(SQLAEnum(AnnouncementType))
    text: Mapped[Optional[str]] = mapped_column(String)
    behavior_type: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(String)
    rating: Mapped[Optional[str]] = mapped_column(String(50))
    subject: Mapped[Optional[str]] = mapped_column(String(255))
    day_id: Mapped[int] = mapped_column(ForeignKey("school_days.id"))

    day: Mapped["SchoolDay"] = relationship(back_populates="announcements")

    @validates("type")
    def validate_type(
        self, key: str, value: str | AnnouncementType
    ) -> AnnouncementType:
        """Validate announcement type"""
        if isinstance(value, AnnouncementType):
            return value
        try:
            return AnnouncementType(value.lower())
        except ValueError:
            raise ValueError("type must be either 'behavior' or 'general'")
