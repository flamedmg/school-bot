from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, NonNegativeInt

class Student(BaseModel):
    """Student information model"""
    nickname: str = Field(
        ..., 
        description="Unique identifier for the student",
        examples=["student1"]
    )
    email: EmailStr = Field(
        ..., 
        description="Student's school email",
        examples=["student@school.example.com"]
    )
    password: str = Field(
        ..., 
        description="Student's school password",
        examples=["password123"]
    )
    emoji: str = Field(
        default="👤", 
        description="Emoji representing the student",
        examples=["🐱", "🐭"]
    )

class CrawlEvent(BaseModel):
    """Event emitted to trigger schedule crawling"""
    timestamp: datetime = Field(
        ..., 
        description="Time when the crawl event was emitted",
        examples=[datetime.now()]
    )
    student: Student = Field(
        ..., 
        description="Student information for crawling"
    )

class MarkEvent(BaseModel):
    """Event emitted when a new mark is detected"""
    student_nickname: str = Field(
        ..., 
        description="Student's unique identifier",
        examples=["student1"]
    )
    subject: str = Field(
        ..., 
        description="Subject the mark is for",
        examples=["Mathematics", "Physics"]
    )
    new: str = Field(
        ..., 
        description="The new mark value",
        examples=["A", "9", "10"]
    )
    lesson_id: str = Field(
        ..., 
        description="Unique identifier of the lesson",
        examples=["math_20240315_1"]
    )

class AnnouncementEvent(BaseModel):
    """Event emitted when a new announcement is detected"""
    student_nickname: str = Field(
        ..., 
        description="Student's unique identifier",
        examples=["student1"]
    )
    text: str = Field(
        ..., 
        description="Announcement text content",
        examples=["Class canceled tomorrow"]
    )
    type: str = Field(
        default="general",
        description="Type of announcement",
        examples=["general", "homework", "behavior"]
    )
    behavior_type: Optional[str] = Field(
        None,
        description="Type of behavior (if behavior announcement)",
        examples=["positive", "negative"]
    )
    description: Optional[str] = Field(
        None,
        description="Additional description",
        examples=["Student helped classmates"]
    )
    rating: Optional[str] = Field(
        None,
        description="Behavior rating",
        examples=["excellent", "good", "needs improvement"]
    )
    subject: Optional[str] = Field(
        None,
        description="Related subject",
        examples=["Mathematics", "Physics"]
    )

class TelegramMessageEvent(BaseModel):
    """Event emitted when a Telegram message is received"""
    message_id: NonNegativeInt = Field(
        ..., 
        description="Telegram message identifier",
        examples=[12345]
    )
    chat_id: int = Field(
        ..., 
        description="Telegram chat identifier",
        examples=[-100123456789]
    )
    text: str = Field(
        ..., 
        description="Message text content",
        examples=["Hello, bot!"]
    )
    date: datetime = Field(
        ..., 
        description="Message timestamp",
        examples=[datetime.now()]
    )

class TelegramCommandEvent(BaseModel):
    """Event emitted when a Telegram command is received"""
    command: str = Field(
        ..., 
        description="Command name without slash",
        examples=["start", "help", "schedule"]
    )
    args: List[str] = Field(
        default_factory=list,
        description="Command arguments",
        examples=[["today"], ["week", "next"]]
    )
    chat_id: int = Field(
        ..., 
        description="Telegram chat identifier",
        examples=[-100123456789]
    )
    message_id: NonNegativeInt = Field(
        ..., 
        description="Telegram message identifier",
        examples=[12345]
    )
    date: datetime = Field(
        ..., 
        description="Command timestamp",
        examples=[datetime.now()]
    )

# Event topic constants
class EventTopics:
    CRAWL_SCHEDULE = "crawl.schedule"
    NEW_MARK = "schedule.new_mark"
    NEW_ANNOUNCEMENT = "schedule.new_announcement"
    TELEGRAM_MESSAGE = "telegram.message"
    TELEGRAM_COMMAND = "telegram.command"
