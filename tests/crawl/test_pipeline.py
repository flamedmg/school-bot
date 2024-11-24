import pytest
from pathlib import Path
from datetime import datetime
from src.schedule.crawler import JSON_SCHEMA
from src.schedule.preprocess import create_default_pipeline
from src.schedule.schema import (
    Schedule,
    SchoolDay,
    Lesson,
    Homework,
    Attachment,
    Link,
    Announcement,
    AnnouncementType,
)
from .utils import load_test_file
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy


def test_schedule_pipeline_output(capsys):
    """Test full pipeline processing and validate using Pydantic models"""
    # Extract data using strategy
    strategy = JsonCssExtractionStrategy(JSON_SCHEMA)
    html = load_test_file("schedule_test1_full.html", base_dir="test_data")
    raw_data = strategy.extract(html=html, url="https://test.com")

    # Add nickname to raw data for testing
    if isinstance(raw_data, list) and len(raw_data) > 0:
        raw_data[0]["nickname"] = "test_student"

    # Create pipeline with markdown output
    output_dir = Path(__file__).parent / "test_data"
    test_output_path = output_dir / "schedule_test_output.md"
    pipeline = create_default_pipeline(markdown_output_path=test_output_path)

    # Execute pipeline without capturing output
    with capsys.disabled():
        print("\nExecuting pipeline steps:")
        final_data = pipeline.execute(raw_data)

    # Validate pipeline output using Pydantic models
    assert final_data is not None
    assert isinstance(final_data, list)
    assert len(final_data) > 0

    try:
        # Create Schedule object from pipeline output
        schedule = Schedule(**final_data[0])

        # Validate Schedule
        assert len(schedule.days) > 0
        assert isinstance(schedule.unique_id, str)
        assert len(schedule.unique_id) == 8  # YYYYWW format
        assert schedule.nickname == "test_student"  # Validate nickname

        # Validate each day
        for day in schedule.days:
            assert isinstance(day, SchoolDay)
            assert isinstance(day.date, datetime)
            assert isinstance(day.unique_id, str)
            assert len(day.unique_id) == 8  # YYYYMMDD format

            # Validate lessons
            for lesson in day.lessons:
                assert isinstance(lesson, Lesson)
                assert isinstance(lesson.index, int) or lesson.index is None
                assert isinstance(lesson.subject, str)
                assert lesson.unique_id.startswith(day.unique_id)

                # Validate homework if present
                if lesson.homework:
                    assert isinstance(lesson.homework, Homework)
                    assert lesson.homework.unique_id.startswith(day.unique_id)

                    # Validate homework attachments
                    for attachment in lesson.homework.attachments:
                        assert isinstance(attachment, Attachment)
                        assert attachment.unique_id.startswith(day.unique_id)
                        assert isinstance(attachment.filename, str)
                        assert isinstance(attachment.url, str)

                    # Validate homework links
                    for link in lesson.homework.links:
                        assert isinstance(link, Link)
                        assert link.unique_id.startswith(day.unique_id)
                        assert isinstance(link.original_url, str)

                # Validate mark if present
                if lesson.mark is not None:
                    assert isinstance(lesson.mark, int)
                    assert 1 <= lesson.mark <= 10

            # Validate announcements
            for announcement in day.announcements:
                assert isinstance(announcement, Announcement)
                assert announcement.unique_id.startswith(day.unique_id)
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
            f"Failed to validate pipeline output with Pydantic models: {str(e)}"
        )

    # Cleanup test output file
    test_output_path.unlink(missing_ok=True)
