from datetime import datetime
from pathlib import Path

import pytest
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
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
from src.schedule.crawler import JSON_SCHEMA
from src.schedule.preprocess import create_default_pipeline

from .utils import load_test_file


@pytest.fixture
def db():
    """Create a test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_schedule_pipeline_output(db, capsys):
    """Test full pipeline processing and validate using database models"""
    # Extract data using strategy
    strategy = JsonCssExtractionStrategy(JSON_SCHEMA)
    html = load_test_file("schedule_test1_full.html", base_dir="test_data")
    raw_data = strategy.extract(html=html, url="https://test.com")

    # Create pipeline with markdown output and nickname
    output_dir = Path(__file__).parent / "test_data"
    test_output_path = output_dir / "schedule_test_output.md"
    pipeline = create_default_pipeline(
        markdown_output_path=test_output_path, nickname="test_student"
    )

    # Execute pipeline without capturing output
    with capsys.disabled():
        print("\nExecuting pipeline steps:")
        schedule = pipeline.execute(raw_data)

    # Validate pipeline output using database models
    assert schedule is not None
    assert isinstance(schedule, Schedule)

    try:
        # Add to database to trigger ID generation and validations
        db.add(schedule)
        db.flush()

        # Validate Schedule
        assert len(schedule.days) > 0
        assert isinstance(schedule.id, str)
        assert len(schedule.id) == 6  # YYYYWW format (6 characters)
        assert schedule.nickname == "test_student"  # Validate nickname

        # Validate each day
        for day in schedule.days:
            assert isinstance(day, SchoolDay)
            assert isinstance(day.date, datetime)
            assert isinstance(day.id, str)
            assert len(day.id) == 8  # YYYYMMDD format

            # Validate lessons
            for lesson in day.lessons:
                assert isinstance(lesson, Lesson)
                assert isinstance(lesson.index, int) or lesson.index is None
                assert isinstance(lesson.subject, str)
                assert lesson.id.startswith(day.id)

                # Validate homework if present
                if lesson.homework:
                    assert isinstance(lesson.homework, Homework)
                    assert lesson.homework.id.startswith(day.id)

                    # Validate homework attachments
                    for attachment in lesson.homework.attachments:
                        assert isinstance(attachment, Attachment)
                        assert attachment.id.startswith(day.id)
                        assert isinstance(attachment.filename, str)
                        assert isinstance(attachment.url, str)

                    # Validate homework links
                    for link in lesson.homework.links:
                        assert isinstance(link, Link)
                        assert link.id.startswith(day.id)
                        assert isinstance(link.original_url, str)

                # Validate mark if present
                if lesson.mark is not None:
                    assert isinstance(lesson.mark, int)
                    assert 1 <= lesson.mark <= 10

            # Validate announcements
            for announcement in day.announcements:
                assert isinstance(announcement, Announcement)
                assert announcement.id.startswith(day.id)
                assert isinstance(announcement.type, AnnouncementType)

                if announcement.type == AnnouncementType.BEHAVIOR:
                    assert announcement.behavior_type is not None
                    assert announcement.description is not None
                    assert announcement.rating is not None
                    assert announcement.subject is not None
                else:
                    assert announcement.text is not None

        print(f"\nSuccessfully validated Schedule with {len(schedule.days)} days")

    except Exception as e:
        pytest.fail(
            f"Failed to validate pipeline output with database models: {str(e)}"
        )

    # Cleanup test output file
    test_output_path.unlink(missing_ok=True)
