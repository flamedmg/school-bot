from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, NonNegativeInt


class Student(BaseModel):
    """Student information model"""

    nickname: str = Field(
        ..., description="Unique identifier for the student", examples=["student1"]
    )
    username: str = Field(
        ..., description="Student's school username", examples=["student123"]
    )
    password: str = Field(
        ..., description="Student's school password", examples=["password123"]
    )
    emoji: str = Field(
        default="👤",
        description="Emoji representing the student",
        examples=["🐱", "🐭"],
    )


class CrawlEvent(BaseModel):
    """Event emitted to trigger schedule crawling"""

    timestamp: datetime = Field(
        ...,
        description="Time when the crawl event was emitted",
        examples=[datetime.now()],
    )
    student: Student = Field(..., description="Student information for crawling")


class MarkEvent(BaseModel):
    """Event emitted when a new mark is detected"""

    student_nickname: str = Field(
        ..., description="Student's unique identifier", examples=["student1"]
    )
    subject: str = Field(
        ..., description="Subject the mark is for", examples=["Mathematics", "Physics"]
    )
    new: str = Field(..., description="The new mark value", examples=["A", "9", "10"])
    lesson_id: str = Field(
        ..., description="Unique identifier of the lesson", examples=["math_20240315_1"]
    )


class AnnouncementEvent(BaseModel):
    """Event emitted when a new announcement is detected"""

    student_nickname: str = Field(
        ..., description="Student's unique identifier", examples=["student1"]
    )
    text: str = Field(
        ...,
        description="Announcement text content",
        examples=["Class canceled tomorrow"],
    )
    type: str = Field(
        default="general",
        description="Type of announcement",
        examples=["general", "homework", "behavior"],
    )
    behavior_type: Optional[str] = Field(
        None,
        description="Type of behavior (if behavior announcement)",
        examples=["positive", "negative"],
    )
    description: Optional[str] = Field(
        None,
        description="Additional description",
        examples=["Student helped classmates"],
    )
    rating: Optional[str] = Field(
        None,
        description="Behavior rating",
        examples=["excellent", "good", "needs improvement"],
    )
    subject: Optional[str] = Field(
        None, description="Related subject", examples=["Mathematics", "Physics"]
    )


class TelegramMessageEvent(BaseModel):
    """Event emitted when a Telegram message is received"""

    message_id: NonNegativeInt = Field(
        ..., description="Telegram message identifier", examples=[12345]
    )
    chat_id: int = Field(
        ..., description="Telegram chat identifier", examples=[-100123456789]
    )
    text: str = Field(..., description="Message text content", examples=["Hello, bot!"])
    date: datetime = Field(
        ..., description="Message timestamp", examples=[datetime.now()]
    )


class TelegramCommandEvent(BaseModel):
    """Event emitted when a Telegram command is received"""

    command: str = Field(
        ...,
        description="Command name without slash",
        examples=["start", "help", "schedule"],
    )
    args: List[str] = Field(
        default_factory=list,
        description="Command arguments",
        examples=[["today"], ["week", "next"]],
    )
    chat_id: int = Field(
        ..., description="Telegram chat identifier", examples=[-100123456789]
    )
    message_id: NonNegativeInt = Field(
        ..., description="Telegram message identifier", examples=[12345]
    )
    date: datetime = Field(
        ..., description="Command timestamp", examples=[datetime.now()]
    )


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
