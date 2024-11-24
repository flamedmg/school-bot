import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base
from src.database.repository import ScheduleRepository
from src.schedule.schema import (
    Schedule as ScheduleModel,
    SchoolDay,
    Lesson,
    Homework,
    Link,
    Attachment,
    Announcement,
    AnnouncementType,
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


@pytest.fixture
def repository(db_session):
    """Create a repository instance"""
    return ScheduleRepository(db_session)


@pytest.fixture
def sample_day():
    """Create a sample school day for testing"""
    return SchoolDay(date=datetime(2024, 1, 1), lessons=[], announcements=[])


@pytest.fixture
def sample_schedule(sample_day):
    """Create a sample schedule with one day"""
    return ScheduleModel(days=[sample_day], nickname="test_student")


@pytest.fixture
def sample_lesson(sample_day):
    """Create a sample lesson with homework"""
    homework = Homework(
        text="Do exercises 1-5",
        links=[
            Link(
                original_url="http://example.com",
                destination_url="http://final.com",
            )
        ],
        attachments=[Attachment(filename="math.pdf", url="/files/math.pdf")],
    )
    # Set parent references for homework and its nested objects
    homework._day = sample_day
    for link in homework.links:
        link._day = sample_day
    for attachment in homework.attachments:
        attachment._day = sample_day

    lesson = Lesson(
        index=1,
        subject="Math",
        room="101",
        topic="Algebra",
        mark=8,
        homework=homework,
    )
    lesson._day = sample_day
    return lesson


@pytest.fixture
def sample_announcement(sample_day):
    """Create a sample behavior announcement"""
    announcement = Announcement(
        type=AnnouncementType.BEHAVIOR,
        behavior_type="Good",
        description="Active participation",
        rating="positive",
        subject="Math",
        text=None,
    )
    announcement._day = sample_day
    return announcement


@pytest.fixture
def sample_general_announcement(sample_day):
    """Create a sample general announcement"""
    announcement = Announcement(
        type=AnnouncementType.GENERAL,
        text="School closed tomorrow",
        behavior_type=None,
        description=None,
        rating=None,
        subject=None,
    )
    announcement._day = sample_day
    return announcement


@pytest.fixture
def sample_day_with_announcement(sample_day, sample_announcement):
    """Create a sample day with an announcement"""
    sample_day.announcements.append(sample_announcement)
    return sample_day


def test_create_day(repository, sample_schedule, sample_day):
    """Test creating a new day"""
    # First create the schedule
    db_schedule = repository._create_schedule(sample_schedule)
    repository.session.add(db_schedule)
    repository.session.flush()

    # Now create the day
    db_day = repository._create_day(sample_day)
    db_day.schedule_id = db_schedule.id
    db_schedule.days.append(db_day)

    assert db_day.unique_id == "20240101"  # Verify YYYYMMDD format
    assert db_day.date == sample_day.date
    assert len(db_day.lessons) == 0
    assert len(db_day.announcements) == 0
    assert db_day.schedule_id == db_schedule.id


def test_create_lesson(repository, sample_schedule, sample_day, sample_lesson):
    """Test creating a new lesson"""
    # First create schedule and day
    db_schedule = repository._create_schedule(sample_schedule)
    repository.session.add(db_schedule)
    repository.session.flush()

    db_day = repository._create_day(sample_day)
    db_day.schedule_id = db_schedule.id
    db_schedule.days.append(db_day)
    repository.session.flush()

    # Now create the lesson
    db_lesson = repository._create_lesson(sample_lesson)
    db_lesson.day_id = db_day.id
    db_day.lessons.append(db_lesson)

    # Verify lesson data
    assert db_lesson.unique_id.startswith("20240101")
    assert db_lesson.index == sample_lesson.index
    assert db_lesson.subject == sample_lesson.subject
    assert db_lesson.room == sample_lesson.room
    assert db_lesson.topic == sample_lesson.topic
    assert db_lesson.mark == sample_lesson.mark

    # Test homework creation
    assert db_lesson.homework is not None
    assert db_lesson.homework.text == sample_lesson.homework.text
    assert len(db_lesson.homework.links) == 1
    assert len(db_lesson.homework.attachments) == 1

    # Verify relationships
    assert db_lesson.day_id == db_day.id
    assert db_day.schedule_id == db_schedule.id


def test_create_homework(repository, sample_schedule, sample_day, sample_lesson):
    """Test creating homework with links and attachments"""
    # First create schedule, day and lesson
    db_schedule = repository._create_schedule(sample_schedule)
    repository.session.add(db_schedule)
    repository.session.flush()

    db_day = repository._create_day(sample_day)
    db_day.schedule_id = db_schedule.id
    db_schedule.days.append(db_day)
    repository.session.flush()

    sample_lesson._day = sample_day
    db_lesson = repository._create_lesson(sample_lesson)
    db_lesson.day_id = db_day.id
    db_day.lessons.append(db_lesson)
    repository.session.flush()

    homework = sample_lesson.homework
    homework._day = sample_day
    for link in homework.links:
        link._day = sample_day
    for attachment in homework.attachments:
        attachment._day = sample_day
    db_homework = repository._create_homework(homework)
    db_lesson.homework = db_homework
    repository.session.flush()

    assert db_homework.unique_id == homework.unique_id
    assert db_homework.text == homework.text
    assert len(db_homework.links) == 1
    assert len(db_homework.attachments) == 1
    assert db_homework.lesson_id == db_lesson.id


def test_create_link(repository, sample_day):
    """Test creating a link"""
    link = Link(original_url="http://example.com", destination_url="http://final.com")
    link._day = sample_day

    db_link = repository._create_link(link)

    assert db_link.unique_id == link.unique_id
    assert db_link.original_url == link.original_url
    assert db_link.destination_url == link.destination_url


def test_create_attachment(repository, sample_day):
    """Test creating an attachment"""
    attachment = Attachment(filename="test.pdf", url="/files/test.pdf")
    attachment._day = sample_day

    db_attachment = repository._create_attachment(attachment)

    assert db_attachment.unique_id == attachment.unique_id
    assert db_attachment.filename == attachment.filename
    assert db_attachment.url == attachment.url


def test_create_announcement(
    repository, sample_schedule, sample_day, sample_announcement
):
    """Test creating an announcement"""
    # First create schedule and day
    db_schedule = repository._create_schedule(sample_schedule)
    repository.session.add(db_schedule)
    repository.session.flush()

    db_day = repository._create_day(sample_day)
    db_day.schedule_id = db_schedule.id
    db_schedule.days.append(db_day)
    repository.session.flush()

    # Create announcement
    sample_announcement._day = sample_day  # Ensure _day is set
    db_announcement = repository._create_announcement(sample_announcement)
    db_announcement.day_id = db_day.id
    db_day.announcements.append(db_announcement)

    assert db_announcement.unique_id == sample_announcement.unique_id
    assert db_announcement.type == sample_announcement.type.value.upper()
    assert db_announcement.behavior_type == sample_announcement.behavior_type
    assert db_announcement.description == sample_announcement.description
    assert db_announcement.rating == sample_announcement.rating
    assert db_announcement.subject == sample_announcement.subject
    assert db_announcement.day_id == db_day.id


def test_process_lessons(repository, sample_day, sample_lesson):
    """Test processing multiple lessons"""
    sample_day.lessons = []  # Clear any existing lessons
    sample_lesson._day = sample_day
    if sample_lesson.homework:
        sample_lesson.homework._day = sample_day
        for link in sample_lesson.homework.links:
            link._day = sample_day
        for attachment in sample_lesson.homework.attachments:
            attachment._day = sample_day
    sample_day.lessons.append(sample_lesson)
    db_day = repository._create_day(sample_day)

    assert len(db_day.lessons) == 1
    assert db_day.lessons[0].subject == "Math"


def test_process_announcements(repository, sample_day, sample_announcement):
    """Test processing multiple announcements"""
    sample_day.announcements = []  # Clear any existing announcements
    sample_announcement._day = sample_day  # Ensure _day is set
    sample_day.announcements.append(sample_announcement)
    db_day = repository._create_day(sample_day)

    assert len(db_day.announcements) == 1
    assert db_day.announcements[0].type == "BEHAVIOR"


def test_update_day(repository, sample_day, sample_lesson, sample_announcement):
    """Test updating an existing day"""
    # Create initial day
    db_day = repository._create_day(sample_day)

    # Add lesson and announcement
    sample_lesson._day = sample_day
    if sample_lesson.homework:
        sample_lesson.homework._day = sample_day
        for link in sample_lesson.homework.links:
            link._day = sample_day
        for attachment in sample_lesson.homework.attachments:
            attachment._day = sample_day
    sample_announcement._day = sample_day
    sample_day.lessons = [sample_lesson]
    sample_day.announcements = [sample_announcement]

    # Update day
    updated_db_day = repository._update_day(db_day, sample_day)

    assert len(updated_db_day.lessons) == 1
    assert len(updated_db_day.announcements) == 1
    assert updated_db_day.lessons[0].subject == "Math"
    assert updated_db_day.announcements[0].type == "BEHAVIOR"


def test_update_schedule(repository):
    """Test updating complete schedule"""
    # Create initial schedule
    initial_schedule = ScheduleModel(days=[SchoolDay(date=datetime(2024, 1, 1))], nickname="test_student")
    db_schedule = repository._create_schedule(initial_schedule)

    # Create updated schedule with a general announcement
    day = SchoolDay(date=datetime(2024, 1, 1))
    lesson = Lesson(index=1, subject="Math")
    lesson._day = day
    announcement = Announcement(
        type=AnnouncementType.GENERAL,
        text="Test announcement",
        behavior_type=None,
        description=None,
        rating=None,
        subject=None,
    )
    announcement._day = day
    day.lessons = [lesson]
    day.announcements = [announcement]
    updated_schedule = ScheduleModel(days=[day], nickname="test_student")

    # Update schedule
    repository._update_schedule(db_schedule, updated_schedule)

    assert len(db_schedule.days) == 1
    assert len(db_schedule.days[0].lessons) == 1
    assert len(db_schedule.days[0].announcements) == 1
