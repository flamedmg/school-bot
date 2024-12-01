from datetime import UTC, datetime
import hashlib
from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.models import (
    Announcement,
    AnnouncementType,
    Attachment,
    Base,
    Homework,
    Lesson,
    Link,
    Schedule,
    SchoolDay,
)


@pytest.fixture
def db():
    """Create a test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def generate_hash(content: str) -> str:
    """Generate a hash from content"""
    return hashlib.md5(content.encode()).hexdigest()[:6]


def test_schedule_nickname_validation(db):
    """Test nickname validation for Schedule model"""
    schedule = Schedule(id="202401", nickname="test_student")
    db.add(schedule)
    db.flush()
    assert schedule.nickname == "test_student"

    # Invalid nicknames
    with pytest.raises(ValueError):
        invalid_schedule = Schedule(id="202401", nickname="")
        db.add(invalid_schedule)
        db.flush()

    with pytest.raises(ValueError):
        invalid_schedule = Schedule(id="202401", nickname="   ")
        db.add(invalid_schedule)
        db.flush()


def test_school_day_date_validation(db):
    """Test date validation for SchoolDay model"""
    schedule = Schedule(id="202401", nickname="test_student")
    db.add(schedule)
    db.flush()

    # Valid date (timezone-naive gets converted to UTC)
    day1 = SchoolDay(id="20240101", date=datetime(2024, 1, 1), schedule=schedule)
    db.add(day1)
    db.flush()
    assert day1.date.tzinfo is not None

    # Valid date (timezone-aware stays as is)
    day2 = SchoolDay(
        id="20240102", date=datetime(2024, 1, 2, tzinfo=UTC), schedule=schedule
    )
    db.add(day2)
    db.flush()
    assert day2.date.tzinfo is not None

    # Invalid date (None)
    with pytest.raises(ValueError):
        invalid_day = SchoolDay(id="20240103", date=None, schedule=schedule)
        db.add(invalid_day)
        db.flush()


def test_lesson_index_validation(db):
    """Test index validation for Lesson model"""
    schedule = Schedule(id="202401", nickname="test_student")
    day = SchoolDay(id="20240101", date=datetime(2024, 1, 1), schedule=schedule)
    db.add_all([schedule, day])
    db.flush()

    # Valid index
    lesson = Lesson(id="20240101_01_1", index=1, subject="Math", day=day)
    db.add(lesson)
    db.flush()
    assert lesson.index == 1

    # Invalid index (zero)
    with pytest.raises(ValueError):
        invalid_lesson = Lesson(id="20240101_01_0", index=0, subject="Math", day=day)
        db.add(invalid_lesson)
        db.flush()

    # Invalid index (negative)
    with pytest.raises(ValueError):
        invalid_lesson = Lesson(id="20240101_01_-1", index=-1, subject="Math", day=day)
        db.add(invalid_lesson)
        db.flush()


def test_link_url_validation(db):
    """Test URL validation for Link model"""
    schedule = Schedule(id="202401", nickname="test_student")
    day = SchoolDay(id="20240101", date=datetime(2024, 1, 1), schedule=schedule)
    lesson = Lesson(id="20240101_01_1", index=1, subject="Math", day=day)
    homework = Homework(id="20240101_01_1_hw1", text="Test homework", lesson=lesson)
    db.add_all([schedule, day, lesson, homework])
    db.flush()

    # Valid URLs
    link1 = Link(
        id="20240101_01_1_hw1_l1", original_url="https://example.com", homework=homework
    )
    link2 = Link(
        id="20240101_01_1_hw1_l2",
        original_url="http://test.com/path",
        destination_url="https://final.com",
        homework=homework,
    )
    db.add_all([link1, link2])
    db.flush()

    # Invalid URLs
    with pytest.raises(ValueError):
        invalid_link = Link(
            id="20240101_01_1_hw1_l3", original_url="not-a-url", homework=homework
        )
        db.add(invalid_link)
        db.flush()

    with pytest.raises(ValueError):
        invalid_link = Link(
            id="20240101_01_1_hw1_l4",
            original_url="http://example.com",
            destination_url="not-a-url",
            homework=homework,
        )
        db.add(invalid_link)
        db.flush()

    with pytest.raises(ValueError):
        invalid_link = Link(
            id="20240101_01_1_hw1_l5",
            original_url="ftp://invalid-scheme.com",
            homework=homework,
        )
        db.add(invalid_link)
        db.flush()


def test_attachment_url_validation(db):
    """Test URL and path validation for Attachment model"""
    schedule = Schedule(id="202401", nickname="test_student")
    day = SchoolDay(id="20240101", date=datetime(2024, 1, 1), schedule=schedule)
    lesson = Lesson(id="20240101_01_1", index=1, subject="Math", day=day)
    db.add_all([schedule, day, lesson])
    db.flush()

    # Valid URLs and paths
    att1 = Attachment(
        id="20240101_01_1_a1",
        filename="test1.pdf",
        url="https://example.com/test.pdf",
        lesson=lesson,
    )
    att2 = Attachment(
        id="20240101_01_1_a2",
        filename="test2.pdf",
        url="http://test.com/path/test.pdf",
        lesson=lesson,
    )
    att3 = Attachment(
        id="20240101_01_1_a3",
        filename="test3.pdf",
        url="/local/path/test.pdf",
        lesson=lesson,
    )
    db.add_all([att1, att2, att3])
    db.flush()

    # Invalid URLs and paths
    with pytest.raises(ValueError):
        invalid_att = Attachment(
            id="20240101_01_1_a4", filename="test.pdf", url="not-a-url", lesson=lesson
        )
        db.add(invalid_att)
        db.flush()

    with pytest.raises(ValueError):
        invalid_att = Attachment(
            id="20240101_01_1_a5",
            filename="test.pdf",
            url="ftp://invalid-scheme.com",
            lesson=lesson,
        )
        db.add(invalid_att)
        db.flush()

    with pytest.raises(ValueError):
        invalid_att = Attachment(
            id="20240101_01_1_a6",
            filename="test.pdf",
            url="local/path/without/leading/slash",
            lesson=lesson,
        )
        db.add(invalid_att)
        db.flush()


def test_attachment_id(db):
    """Test attachment ID generation"""
    schedule = Schedule(id="202401", nickname="test_student")
    day = SchoolDay(id="20240101", date=datetime(2024, 1, 1), schedule=schedule)
    lesson = Lesson(id="20240101_01_1", index=1, subject="Math", day=day)
    db.add_all([schedule, day, lesson])
    db.flush()

    # Test that same content gets same ID hash
    content1 = f"test.pdf:/files/test.pdf"
    hash1 = generate_hash(content1)
    att1 = Attachment(
        id=f"20240101_01_1_{hash1}",
        filename="test.pdf",
        url="/files/test.pdf",
        lesson=lesson,
    )
    db.add(att1)
    db.flush()

    # Create another attachment with same content - should get same ID hash
    content2 = f"test.pdf:/files/test.pdf"
    hash2 = generate_hash(content2)
    assert hash2 == hash1

    # Different content should get different ID
    content3 = f"other.pdf:/files/other.pdf"
    hash3 = generate_hash(content3)
    att3 = Attachment(
        id=f"20240101_01_1_{hash3}",
        filename="other.pdf",
        url="/files/other.pdf",
        lesson=lesson,
    )
    db.add(att3)
    db.flush()
    assert hash3 != hash1


def test_link_id(db):
    """Test link ID generation"""
    schedule = Schedule(id="202401", nickname="test_student")
    day = SchoolDay(id="20240101", date=datetime(2024, 1, 1), schedule=schedule)
    lesson = Lesson(id="20240101_01_1", index=1, subject="Math", day=day)
    homework = Homework(id="20240101_01_1_hw1", text="Test homework", lesson=lesson)
    db.add_all([schedule, day, lesson, homework])
    db.flush()

    # Test that same content gets same ID hash
    content1 = f"http://example.com:"
    hash1 = generate_hash(content1)
    link1 = Link(
        id=f"20240101_01_1_hw1_{hash1}",
        original_url="http://example.com",
        homework=homework,
    )
    db.add(link1)
    db.flush()

    # Create another link with same content - should get same ID hash
    content2 = f"http://example.com:"
    hash2 = generate_hash(content2)
    assert hash2 == hash1

    # Different content should get different ID
    content3 = f"http://example.com:http://final.com"
    hash3 = generate_hash(content3)
    link3 = Link(
        id=f"20240101_01_1_hw1_{hash3}",
        original_url="http://example.com",
        destination_url="http://final.com",
        homework=homework,
    )
    db.add(link3)
    db.flush()
    assert hash3 != hash1


def test_homework_id(db):
    """Test homework ID generation"""
    schedule = Schedule(id="202401", nickname="test_student")
    day = SchoolDay(id="20240101", date=datetime(2024, 1, 1), schedule=schedule)
    db.add_all([schedule, day])
    db.flush()

    # Test that same content gets same ID hash
    hw1 = Homework(id="20240101_01_1_hw1", text="Test homework")
    lesson1 = Lesson(id="20240101_01_1", index=1, subject="Math", homework=hw1, day=day)
    db.add(lesson1)
    db.flush()

    # Create another homework with same content - should get same ID hash
    hw2 = Homework(id="20240101_01_1_hw1", text="Test homework")
    # Don't add to DB since it would violate unique constraint, just verify ID
    assert hw2.id == hw1.id

    # Different content should get different ID
    hw3 = Homework(id="20240101_01_3_hw2", text="Different homework")
    lesson3 = Lesson(
        id="20240101_01_3", index=3, subject="Science", homework=hw3, day=day
    )
    db.add(lesson3)
    db.flush()
    assert hw1.id != hw3.id


def test_lesson_id(db):
    """Test lesson ID generation"""
    schedule = Schedule(id="202401", nickname="test_student")
    day = SchoolDay(id="20240101", date=datetime(2024, 1, 1), schedule=schedule)
    lesson = Lesson(id="20240101_01_1", index=1, subject="Math", day=day)
    db.add_all([schedule, day, lesson])
    db.flush()

    assert lesson.id == "20240101_01_1"

    # Test invalid formats
    with pytest.raises(ValueError):
        invalid_lesson = Lesson(id="20240101_1", index=1, subject="Math", day=day)
        db.add(invalid_lesson)
        db.flush()

    with pytest.raises(ValueError):
        invalid_lesson = Lesson(id="2024010_01_1", index=1, subject="Math", day=day)
        db.add(invalid_lesson)
        db.flush()

    with pytest.raises(ValueError):
        invalid_lesson = Lesson(id="20240101_1_1", index=1, subject="Math", day=day)
        db.add(invalid_lesson)
        db.flush()


def test_announcement_id(db):
    """Test announcement ID generation"""
    schedule = Schedule(id="202401", nickname="test_student")
    day = SchoolDay(id="20240101", date=datetime(2024, 1, 1), schedule=schedule)
    db.add_all([schedule, day])
    db.flush()

    behavior = Announcement(
        id="20240101_01_behavior_b1",
        type=AnnouncementType.BEHAVIOR,
        behavior_type="Centīgs",
        description="Good work",
        rating="positive",
        subject="Math",
        day=day,
    )
    general = Announcement(
        id="20240101_01_general_g1",
        type=AnnouncementType.GENERAL,
        text="School meeting tomorrow",
        day=day,
    )
    db.add_all([behavior, general])
    db.flush()

    # Test invalid formats
    with pytest.raises(ValueError):
        invalid_announcement = Announcement(
            id="20240101_behavior_b1",  # Missing DD
            type=AnnouncementType.BEHAVIOR,
            behavior_type="Centīgs",
            description="Good work",
            rating="positive",
            subject="Math",
            day=day,
        )
        db.add(invalid_announcement)
        db.flush()

    with pytest.raises(ValueError):
        invalid_announcement = Announcement(
            id="20240101_01_invalid_g1",  # Invalid type
            type=AnnouncementType.GENERAL,
            text="School meeting tomorrow",
            day=day,
        )
        db.add(invalid_announcement)
        db.flush()


def test_school_day_id(db):
    """Test school day ID generation"""
    schedule = Schedule(id="202401", nickname="test_student")
    day1 = SchoolDay(id="20240101", date=datetime(2024, 1, 1), schedule=schedule)
    day2 = SchoolDay(id="20240102", date=datetime(2024, 1, 2), schedule=schedule)
    day3 = SchoolDay(id="20240108", date=datetime(2024, 1, 8), schedule=schedule)
    db.add_all([schedule, day1, day2, day3])
    db.flush()

    assert day1.id == "20240101"
    assert day2.id == "20240102"
    assert day3.id == "20240108"


def test_schedule_id(db):
    """Test schedule ID generation"""
    schedule = Schedule(
        id="202401",
        nickname="test_student",
        days=[
            SchoolDay(id="20240101", date=datetime(2024, 1, 1)),
            SchoolDay(id="20240102", date=datetime(2024, 1, 2)),
        ],
    )
    db.add(schedule)
    db.flush()

    assert schedule.id == "202401"


def test_announcement_type_validation(db):
    """Test announcement type validation"""
    schedule = Schedule(id="202401", nickname="test_student")
    day = SchoolDay(id="20240101", date=datetime(2024, 1, 1), schedule=schedule)
    db.add_all([schedule, day])
    db.flush()

    # Valid behavior announcement
    behavior = Announcement(
        id="20240101_01_behavior_b1",
        type=AnnouncementType.BEHAVIOR,
        behavior_type="Centīgs",
        description="Good work",
        rating="positive",
        subject="Math",
        day=day,
    )
    db.add(behavior)
    db.flush()
    assert behavior.type == AnnouncementType.BEHAVIOR

    # Valid general announcement
    general = Announcement(
        id="20240101_01_general_g1",
        type=AnnouncementType.GENERAL,
        text="School meeting",
        day=day,
    )
    db.add(general)
    db.flush()
    assert general.type == AnnouncementType.GENERAL

    # Invalid behavior announcement (missing required fields)
    with pytest.raises(ValueError):
        invalid_behavior = Announcement(
            id="20240101_01_behavior_b2",
            type=AnnouncementType.BEHAVIOR,
            day=day,
        )
        db.add(invalid_behavior)
        db.flush()

    # Invalid general announcement (missing text)
    with pytest.raises(ValueError):
        invalid_general = Announcement(
            id="20240101_01_general_g2",
            type=AnnouncementType.GENERAL,
            day=day,
        )
        db.add(invalid_general)
        db.flush()


def test_mark_validation(db):
    """Test mark validation"""
    schedule = Schedule(id="202401", nickname="test_student")
    day = SchoolDay(id="20240101", date=datetime(2024, 1, 1), schedule=schedule)
    db.add_all([schedule, day])
    db.flush()

    # Valid marks
    lesson1 = Lesson(id="20240101_01_1", index=1, subject="Math", mark=1, day=day)
    lesson2 = Lesson(id="20240101_01_2", index=2, subject="Math", mark=10, day=day)
    lesson3 = Lesson(id="20240101_01_3", index=3, subject="Math", mark=None, day=day)
    db.add_all([lesson1, lesson2, lesson3])
    db.flush()

    assert lesson1.mark == 1
    assert lesson2.mark == 10
    assert lesson3.mark is None

    # Invalid marks
    with pytest.raises(ValueError):
        invalid_lesson1 = Lesson(
            id="20240101_01_4", index=4, subject="Math", mark=0, day=day
        )
        db.add(invalid_lesson1)
        db.flush()

    with pytest.raises(ValueError):
        invalid_lesson2 = Lesson(
            id="20240101_01_5", index=5, subject="Math", mark=11, day=day
        )
        db.add(invalid_lesson2)
        db.flush()


def test_subject_validation(db):
    """Test subject validation"""
    schedule = Schedule(id="202401", nickname="test_student")
    day = SchoolDay(id="20240101", date=datetime(2024, 1, 1), schedule=schedule)
    db.add_all([schedule, day])
    db.flush()

    # Valid subject
    lesson = Lesson(id="20240101_01_1", index=1, subject="Math", day=day)
    db.add(lesson)
    db.flush()
    assert lesson.subject == "Math"

    # Invalid subjects
    with pytest.raises(ValueError):
        invalid_lesson1 = Lesson(id="20240101_01_2", index=2, subject="", day=day)
        db.add(invalid_lesson1)
        db.flush()

    with pytest.raises(ValueError):
        invalid_lesson2 = Lesson(id="20240101_01_3", index=3, subject="   ", day=day)
        db.add(invalid_lesson2)
        db.flush()
