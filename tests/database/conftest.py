from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import (
    Announcement,
    AnnouncementType,
    Base,
    Homework,
    Lesson,
    Schedule,
    SchoolDay,
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
    session_local = sessionmaker(bind=engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


def create_lesson(
    index: int,
    subject: str,
    mark: int | None = None,
    room: str | None = None,
    topic: str | None = None,
    homework: Homework | None = None,
    day: SchoolDay | None = None,
) -> Lesson:
    """Create a lesson with proper parent references"""
    # Create id based on day and index
    day_id = day.id if day else "20240101"
    id = f"{day_id}_{index}"

    lesson = Lesson(
        id=id,
        index=index,
        subject=subject,
        mark=mark,
        room=room,
        topic=topic,
        homework=homework,
        day=day,
    )
    return lesson


def create_announcement(
    type: AnnouncementType,
    text: str | None = None,
    behavior_type: str | None = None,
    description: str | None = None,
    rating: str | None = None,
    subject: str | None = None,
    day: SchoolDay | None = None,
) -> Announcement:
    """Create an announcement with proper parent references"""
    # Create id based on day and type
    day_id = day.id if day else "20240101"
    type_prefix = "b" if type == AnnouncementType.BEHAVIOR else "g"
    content = f"{type.value}:{text or ''}:{behavior_type or ''}:{description or ''}"
    content_hash = f"{type_prefix}{''.join(c for c in content if c.isalnum())[:6]}"
    id = f"{day_id}_{content_hash}"

    announcement = Announcement(
        id=id,
        type=type,
        text=text,
        behavior_type=behavior_type,
        description=description,
        rating=rating,
        subject=subject,
        day=day,
    )
    return announcement


def create_school_day(
    date: datetime,
    lessons: list[Lesson] | None = None,
    announcements: list[Announcement] | None = None,
) -> SchoolDay:
    """Create a school day with proper parent references"""
    day = SchoolDay(
        id=date.strftime("%Y%m%d"),
        date=date,
        lessons=lessons or [],
        announcements=announcements or [],
    )
    return day


def create_schedule(days: list[SchoolDay], nickname: str = "test_student") -> Schedule:
    """Create a schedule with proper parent references"""
    # Get first day to generate schedule id
    first_day = days[0] if days else None
    schedule_id = first_day.id[:6] if first_day else "202401"

    schedule = Schedule(
        id=schedule_id,
        days=days,
        nickname=nickname,
    )
    # Set schedule reference for days
    for day in days:
        day.schedule = schedule
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
    day = SchoolDay(
        id=sample_date.strftime("%Y%m%d"),
        date=sample_date,
    )
    lesson = make_lesson(index=1, subject="Math", mark=8, day=day)
    announcement = make_announcement(
        type=AnnouncementType.GENERAL, text="Initial announcement", day=day
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
    day = SchoolDay(
        id=sample_date.strftime("%Y%m%d"),
        date=sample_date,
    )
    lesson = make_lesson(
        index=1,  # Same index to maintain id
        subject="Advanced Math",
        mark=9,
        day=day,
    )
    day.lessons = [lesson]
    return day


@pytest.fixture
def modified_schedule(modified_day):
    """Create a modified version of the sample schedule"""
    return create_schedule(days=[modified_day])


@pytest.fixture
def lesson_order_day(sample_date, make_lesson):
    """Create a day with two lessons in a specific order"""
    day = SchoolDay(
        id=sample_date.strftime("%Y%m%d"),
        date=sample_date,
    )
    lesson1 = make_lesson(index=1, subject="Math", day=day)
    lesson2 = make_lesson(index=2, subject="Physics", day=day)
    day.lessons = [lesson1, lesson2]
    return day


@pytest.fixture
def reversed_lesson_order_day(sample_date, make_lesson):
    """Create a day with two lessons in reversed order"""
    day = SchoolDay(
        id=sample_date.strftime("%Y%m%d"),
        date=sample_date,
    )
    lesson1 = make_lesson(index=1, subject="Math", day=day)
    lesson2 = make_lesson(index=2, subject="Physics", day=day)
    day.lessons = [lesson2, lesson1]  # Reversed order
    return day
