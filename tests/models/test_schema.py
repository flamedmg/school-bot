from datetime import datetime
import pytest
from urllib.parse import urlparse
from src.schedule.schema import (
    AnnouncementType,
    Attachment,
    Link,
    Homework,
    Lesson,
    Announcement,
    SchoolDay,
    Schedule,
)


def is_valid_url_or_path(v: str) -> str:
    """Validate URL or path format"""
    if v.startswith(("http://", "https://")):
        # Validate as URL
        result = urlparse(v)
        if all([result.scheme, result.netloc]):
            return v
    elif v.startswith("/"):
        # Validate as path
        return v
    raise ValueError("Must be a valid URL or path starting with /")


def test_url_validation():
    """Test URL and path validation"""
    # Valid cases
    assert is_valid_url_or_path("https://example.com") == "https://example.com"
    assert is_valid_url_or_path("http://test.com/path") == "http://test.com/path"
    assert is_valid_url_or_path("/local/path") == "/local/path"

    # Invalid cases
    with pytest.raises(ValueError):
        is_valid_url_or_path("not-a-url")
    with pytest.raises(ValueError):
        is_valid_url_or_path("ftp://invalid-scheme.com")


def test_attachment_unique_id():
    """Test attachment unique ID generation"""
    day = SchoolDay(date=datetime(2024, 1, 1))
    att1 = Attachment(filename="test.pdf", url="/files/test.pdf")
    att2 = Attachment(filename="test.pdf", url="/files/test.pdf")
    att3 = Attachment(filename="other.pdf", url="/files/other.pdf")

    # Set day reference
    att1._day = day
    att2._day = day
    att3._day = day

    # Test format: YYYYMMDD_hash
    assert att1.unique_id.startswith("20240101_")
    assert len(att1.unique_id.split("_")[1]) == 6  # 6-char hash

    # Same content should have same ID
    assert att1.unique_id == att2.unique_id
    # Different content should have different ID
    assert att1.unique_id != att3.unique_id


def test_link_unique_id():
    """Test link unique ID generation"""
    day = SchoolDay(date=datetime(2024, 1, 1))
    link1 = Link(original_url="http://example.com")
    link2 = Link(original_url="http://example.com")
    link3 = Link(original_url="http://example.com", destination_url="http://final.com")

    # Set day reference
    link1._day = day
    link2._day = day
    link3._day = day

    # Test format: YYYYMMDD_hash
    assert link1.unique_id.startswith("20240101_")
    assert len(link1.unique_id.split("_")[1]) == 6  # 6-char hash

    # Same content should have same ID
    assert link1.unique_id == link2.unique_id
    # Different content should have different ID
    assert link1.unique_id != link3.unique_id


def test_homework_unique_id():
    """Test homework unique ID generation"""
    day = SchoolDay(date=datetime(2024, 1, 1))
    hw1 = Homework(text="Test homework")
    hw2 = Homework(text="Test homework")
    hw3 = Homework(text="Different homework")

    # Set day reference
    hw1._day = day
    hw2._day = day
    hw3._day = day

    # Test format: YYYYMMDD_hash
    assert hw1.unique_id.startswith("20240101_")
    assert len(hw1.unique_id.split("_")[1]) == 6  # 6-char hash

    # Same content should have same ID
    assert hw1.unique_id == hw2.unique_id
    # Different content should have different ID
    assert hw1.unique_id != hw3.unique_id


def test_lesson_unique_id():
    """Test lesson unique ID generation"""
    day = SchoolDay(date=datetime(2024, 1, 1))
    lesson = Lesson(index=1, subject="Math")
    day.append_lesson(lesson)

    assert lesson.unique_id == f"{day.unique_id}_1"

    # Test lesson without day
    lesson2 = Lesson(index=1, subject="Math")
    with pytest.raises(ValueError, match="Lesson must be associated with a day"):
        _ = lesson2.unique_id


def test_announcement_unique_id():
    """Test announcement unique ID generation"""
    day = SchoolDay(date=datetime(2024, 1, 1))

    behavior = Announcement(
        type=AnnouncementType.BEHAVIOR,
        behavior_type="Centīgs",
        description="Good work",
        rating="positive",
        subject="Math",
    )
    day.append_announcement(behavior)

    general = Announcement(
        type=AnnouncementType.GENERAL, text="School meeting tomorrow"
    )
    day.append_announcement(general)

    # Test format: YYYYMMDD_[b|g]hash
    assert behavior.unique_id.startswith("20240101_b")
    assert general.unique_id.startswith("20240101_g")
    assert len(behavior.unique_id.split("_")[1]) == 7  # b + 6 chars
    assert len(general.unique_id.split("_")[1]) == 7  # g + 6 chars


def test_school_day_unique_id():
    """Test school day unique ID generation"""
    day1 = SchoolDay(date=datetime(2024, 1, 1))
    day2 = SchoolDay(date=datetime(2024, 1, 2))
    day3 = SchoolDay(date=datetime(2024, 1, 8))

    assert day1.unique_id == "20240101"
    assert day2.unique_id == "20240102"
    assert day3.unique_id == "20240108"


def test_schedule_unique_id():
    """Test schedule unique ID generation"""
    schedule = Schedule(
        nickname="test_student",
        days=[
            SchoolDay(date=datetime(2024, 1, 1)),
            SchoolDay(date=datetime(2024, 1, 2)),
        ]
    )

    assert schedule.unique_id == "202401"

    # Test empty schedule
    with pytest.raises(ValueError, match="Schedule must have at least one day"):
        Schedule(nickname="test_student", days=[]).unique_id


def test_announcement_type_validation():
    """Test announcement type validation"""
    # Valid behavior announcement
    behavior = Announcement(
        type=AnnouncementType.BEHAVIOR,
        behavior_type="Centīgs",
        description="Good work",
        rating="positive",
        subject="Math",
    )
    assert behavior.type == AnnouncementType.BEHAVIOR

    # Valid general announcement
    general = Announcement(type=AnnouncementType.GENERAL, text="School meeting")
    assert general.type == AnnouncementType.GENERAL

    # Invalid behavior announcement (missing required fields)
    with pytest.raises(ValueError):
        Announcement(type=AnnouncementType.BEHAVIOR)

    # Invalid general announcement (missing text)
    with pytest.raises(ValueError):
        Announcement(type=AnnouncementType.GENERAL)


def test_mark_validation():
    """Test mark validation"""
    # Valid marks
    assert Lesson(index=1, subject="Math", mark=1).mark == 1
    assert Lesson(index=1, subject="Math", mark=10).mark == 10
    assert Lesson(index=1, subject="Math", mark=None).mark is None

    # Invalid marks
    with pytest.raises(ValueError):
        Lesson(index=1, subject="Math", mark=0)
    with pytest.raises(ValueError):
        Lesson(index=1, subject="Math", mark=11)


def test_subject_validation():
    """Test subject validation"""
    # Valid subject
    assert Lesson(index=1, subject="Math").subject == "Math"

    # Invalid subjects
    with pytest.raises(ValueError):
        Lesson(index=1, subject="")
    with pytest.raises(ValueError):
        Lesson(index=1, subject="   ")
