import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base
from src.database.repository import ScheduleRepository
from src.crawler.schedule.schema import AnnouncementType

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

def test_check_lesson_order(repository, make_lesson, make_school_day, sample_date):
    """Test lesson order change detection"""
    # Create a day to serve as parent
    day = make_school_day(date=sample_date)
    
    # Create lessons with proper parent reference
    lesson1 = make_lesson(index=1, subject="Math", day=day)
    lesson2 = make_lesson(index=2, subject="Physics", day=day)
    
    # Create days with different lesson orders
    day1 = make_school_day(date=sample_date, lessons=[lesson1, lesson2])
    day2 = make_school_day(date=sample_date, lessons=[lesson2, lesson1])
    
    assert repository._check_lesson_order(day1.lessons, day2.lessons)

def test_check_lesson_marks(repository, make_lesson, make_school_day, sample_date):
    """Test mark change detection"""
    day = make_school_day(date=sample_date)
    lesson = make_lesson(index=1, subject="Math", mark=8, day=day)
    db_lesson = repository._create_lesson(lesson)
    
    # Modify mark
    lesson.mark = 9
    
    changes = repository._check_lesson_marks([lesson], [db_lesson])
    assert len(changes) == 1
    assert changes[0]['old'] == 8
    assert changes[0]['new'] == 9

def test_check_lesson_subjects(repository, make_lesson, make_school_day, sample_date):
    """Test subject change detection"""
    day = make_school_day(date=sample_date)
    lesson = make_lesson(index=1, subject="Math", day=day)
    db_lesson = repository._create_lesson(lesson)
    
    # Modify subject
    lesson.subject = "Advanced Math"
    
    changes = repository._check_lesson_subjects([lesson], [db_lesson])
    assert len(changes) == 1
    assert changes[0]['old'] == "Math"
    assert changes[0]['new'] == "Advanced Math"

def test_check_announcements(repository, make_announcement, make_school_day, sample_date):
    """Test announcement change detection"""
    day = make_school_day(date=sample_date)
    
    # Create initial announcement
    announcement1 = make_announcement(
        type=AnnouncementType.BEHAVIOR,
        behavior_type="Good",
        description="Active participation",
        rating="positive",
        subject="Math",
        day=day
    )
    
    # Create new announcement
    announcement2 = make_announcement(
        type=AnnouncementType.GENERAL,
        text="School closed tomorrow",
        day=day
    )
    
    # Initial state with one announcement
    day.announcements = [announcement1]
    db_day = repository._create_day(day)
    
    # Create new day with different announcement
    new_day = make_school_day(
        date=sample_date,
        announcements=[announcement2]
    )
    
    changes = repository._check_announcements(new_day.announcements, db_day.announcements)
    assert len(changes['added']) == 1
    assert len(changes['removed']) == 1

def test_get_changes_detects_lesson_order_change(repository, lesson_order_day, reversed_lesson_order_day, make_schedule):
    """Test that get_changes detects lesson order changes"""
    # Create and save initial schedule
    initial_schedule = make_schedule(days=[lesson_order_day])
    repository.save_schedule(initial_schedule)
    
    # Create modified schedule with reversed lesson order
    modified_schedule = make_schedule(days=[reversed_lesson_order_day])
    
    # Get changes
    changes = repository.get_changes(modified_schedule)
    
    assert changes["lessons_changed"]

def test_get_changes_detects_multiple_changes(repository, sample_schedule, modified_schedule):
    """Test that get_changes detects multiple types of changes simultaneously"""
    # Save initial schedule
    repository.save_schedule(sample_schedule)
    
    # Get changes using modified schedule
    changes = repository.get_changes(modified_schedule)
    
    assert len(changes["marks"]) == 1
    assert changes["marks"][0]["old"] == 8
    assert changes["marks"][0]["new"] == 9
    assert len(changes["subjects"]) == 1
    assert changes["subjects"][0]["old"] == "Math"
    assert changes["subjects"][0]["new"] == "Advanced Math"
    assert len(changes["announcements"]["removed"]) == 1
    assert not changes["lessons_changed"]
