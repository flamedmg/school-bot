import pytest
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base
from src.crawler.schedule.schema import (
    Schedule as ScheduleModel,
    SchoolDay,
    Lesson,
    Homework,
    Link,
    Attachment,
    Announcement,
    AnnouncementType
)

@pytest.fixture
def engine():
    """Create a fresh in-memory database for each test"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(engine):
    """Create a new database session for each test"""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def create_lesson(
    index: int,
    subject: str,
    mark: Optional[int] = None,
    room: Optional[str] = None,
    topic: Optional[str] = None,
    homework: Optional[Homework] = None,
    day: Optional[SchoolDay] = None
) -> Lesson:
    """Create a lesson with proper parent references"""
    lesson = Lesson(
        index=index,
        subject=subject,
        mark=mark,
        room=room,
        topic=topic,
        homework=homework
    )
    if day:
        lesson._day = day
    return lesson

def create_announcement(
    type: AnnouncementType,
    text: Optional[str] = None,
    behavior_type: Optional[str] = None,
    description: Optional[str] = None,
    rating: Optional[str] = None,
    subject: Optional[str] = None,
    day: Optional[SchoolDay] = None
) -> Announcement:
    """Create an announcement with proper parent references"""
    announcement = Announcement(
        type=type,
        text=text,
        behavior_type=behavior_type,
        description=description,
        rating=rating,
        subject=subject
    )
    if day:
        announcement._day = day
    return announcement

def create_school_day(
    date: datetime,
    lessons: Optional[List[Lesson]] = None,
    announcements: Optional[List[Announcement]] = None
) -> SchoolDay:
    """Create a school day with proper parent references"""
    day = SchoolDay(
        date=date,
        lessons=lessons or [],
        announcements=announcements or []
    )
    # Set parent references
    for lesson in day.lessons:
        lesson._day = day
    for announcement in day.announcements:
        announcement._day = day
    return day

def create_schedule(days: List[SchoolDay]) -> ScheduleModel:
    """Create a schedule with proper parent references"""
    schedule = ScheduleModel(days=days)
    # Ensure each day's lessons and announcements have proper references
    for day in schedule.days:
        for lesson in day.lessons:
            lesson._day = day
        for announcement in day.announcements:
            announcement._day = day
    return schedule

@pytest.fixture
def make_lesson():
    """Fixture that returns the create_lesson function"""
    return create_lesson

@pytest.fixture
def make_announcement():
    """Fixture that returns the create_announcement function"""
    return create_announcement

@pytest.fixture
def make_school_day():
    """Fixture that returns the create_school_day function"""
    return create_school_day

@pytest.fixture
def make_schedule():
    """Fixture that returns the create_schedule function"""
    return create_schedule

@pytest.fixture
def sample_date():
    """Return a consistent date for testing"""
    return datetime(2024, 1, 1)  # Week 1 of 2024

@pytest.fixture
def sample_day(sample_date, make_lesson, make_announcement):
    """Create a sample day with one lesson and one announcement"""
    day = SchoolDay(date=sample_date)
    lesson = make_lesson(
        index=1,
        subject="Math",
        mark=8,
        day=day
    )
    announcement = make_announcement(
        type=AnnouncementType.GENERAL,
        text="Initial announcement",
        day=day
    )
    day.lessons = [lesson]
    day.announcements = [announcement]
    return day

@pytest.fixture
def sample_schedule(sample_day):
    """Create a sample schedule with one day"""
    return create_schedule(days=[sample_day])

@pytest.fixture
def modified_day(sample_date, make_lesson):
    """Create a modified version of the sample day"""
    day = SchoolDay(date=sample_date)
    lesson = make_lesson(
        index=1,  # Same index to maintain unique_id
        subject="Advanced Math",
        mark=9,
        day=day  # Set parent reference
    )
    day.lessons = [lesson]
    # Ensure parent reference is set after assigning to day
    lesson._day = day
    return day

@pytest.fixture
def modified_schedule(modified_day):
    """Create a modified version of the sample schedule"""
    return create_schedule(days=[modified_day])

@pytest.fixture
def lesson_order_day(sample_date, make_lesson):
    """Create a day with two lessons in a specific order"""
    day = SchoolDay(date=sample_date)
    lesson1 = make_lesson(index=1, subject="Math", day=day)
    lesson2 = make_lesson(index=2, subject="Physics", day=day)
    day.lessons = [lesson1, lesson2]
    return day

@pytest.fixture
def reversed_lesson_order_day(sample_date, make_lesson):
    """Create a day with two lessons in reversed order"""
    day = SchoolDay(date=sample_date)
    lesson1 = make_lesson(index=1, subject="Math", day=day)
    lesson2 = make_lesson(index=2, subject="Physics", day=day)
    day.lessons = [lesson2, lesson1]  # Reversed order
    return day
