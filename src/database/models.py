from __future__ import annotations
from datetime import datetime, UTC
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, String, DateTime, Enum as SQLAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase, validates
import enum

if TYPE_CHECKING:
    from .models import Schedule, SchoolDay, Lesson, Homework, Link, Attachment, Announcement

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

class AnnouncementTypeEnum(str, enum.Enum):
    BEHAVIOR = "BEHAVIOR"
    GENERAL = "GENERAL"

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
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC)
    )
    
    days: Mapped[List["SchoolDay"]] = relationship(
        back_populates="schedule", 
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_schedules_nickname_unique_id', 'nickname', 'unique_id', unique=True),
    )

    @validates('unique_id')
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
        back_populates="day",
        cascade="all, delete-orphan"
    )
    announcements: Mapped[List["Announcement"]] = relationship(
        back_populates="day",
        cascade="all, delete-orphan"
    )

    @validates('unique_id')
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
        back_populates="lesson",
        cascade="all, delete-orphan",
        uselist=False
    )

class Homework(Base):
    __tablename__ = "homework"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    unique_id: Mapped[str] = mapped_column(String(20))
    text: Mapped[Optional[str]] = mapped_column(String)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))
    
    lesson: Mapped["Lesson"] = relationship(back_populates="homework")
    links: Mapped[List["Link"]] = relationship(
        back_populates="homework",
        cascade="all, delete-orphan"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        back_populates="homework",
        cascade="all, delete-orphan"
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
    unique_id: Mapped[str] = mapped_column(String(20))
    filename: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(2048))
    homework_id: Mapped[int] = mapped_column(ForeignKey("homework.id"))
    
    homework: Mapped["Homework"] = relationship(back_populates="attachments")

class Announcement(Base):
    __tablename__ = "announcements"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    unique_id: Mapped[str] = mapped_column(String(20))
    type: Mapped[str] = mapped_column(String(50))  # Store as string instead of enum
    text: Mapped[Optional[str]] = mapped_column(String)
    behavior_type: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(String)
    rating: Mapped[Optional[str]] = mapped_column(String(50))
    subject: Mapped[Optional[str]] = mapped_column(String(255))
    day_id: Mapped[int] = mapped_column(ForeignKey("school_days.id"))
    
    day: Mapped["SchoolDay"] = relationship(back_populates="announcements")

    @validates('type')
    def validate_type(self, key: str, value: str) -> str:
        """Validate announcement type"""
        if value not in ('BEHAVIOR', 'GENERAL'):
            raise ValueError("type must be either 'BEHAVIOR' or 'GENERAL'")
        return value
