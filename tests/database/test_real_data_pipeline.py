"""Test full pipeline with real data, including change detection"""

from datetime import datetime
from pathlib import Path

import pytest
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from loguru import logger

from src.database.enums import ChangeType
from src.database.models import (
    Announcement,
    AnnouncementType,
    Base,
    Lesson,
    Schedule,
    SchoolDay,
)
from src.database.repository import ScheduleRepository
from src.schedule.crawler import JSON_SCHEMA
from src.schedule.preprocess import create_default_pipeline
from tests.crawl.utils import load_test_file


@pytest.fixture
async def db_session():
    """Create a new async database session for each test"""
    # Create async engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create async session
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_real_data_pipeline_and_changes(db_session):
    """Test full pipeline with real data, including change detection"""
    # Set up repository
    repository = ScheduleRepository(db_session)

    # Extract data using strategy
    strategy = JsonCssExtractionStrategy(JSON_SCHEMA)
    html = load_test_file("schedule_test1_full.html", base_dir="test_data")
    raw_data = strategy.extract(html=html, url="https://test.com")

    # Create and execute pipeline
    pipeline = create_default_pipeline(nickname="Gavrovska Darjana")
    initial_schedule = pipeline.execute(raw_data)

    # Save to database and get it back to verify the save worked
    db_schedule = await repository.save_schedule(initial_schedule)
    saved_schedule = await repository.get_schedule_by_id(
        db_schedule.id, initial_schedule.nickname
    )
    assert saved_schedule is not None

    # Find a lesson with a mark to modify
    lesson_to_modify = None
    lesson_day = None
    for day in saved_schedule.days:
        for lesson in day.lessons:
            if lesson.mark is not None:
                lesson_to_modify = lesson
                lesson_day = day
                break
        if lesson_to_modify:
            break

    assert lesson_to_modify is not None, "No lesson with mark found"
    logger.info(
        f"Found lesson to modify: {lesson_to_modify.id}, mark={lesson_to_modify.mark}"
    )

    # Create modified schedule with changed mark
    modified_day = SchoolDay(
        id=lesson_day.id,
        date=lesson_day.date,
        lessons=[],
    )

    # Create new lesson with same ID but different mark
    modified_lesson = Lesson(
        id=lesson_to_modify.id,
        index=lesson_to_modify.index,
        subject=lesson_to_modify.subject,
        room=lesson_to_modify.room,
        topic=lesson_to_modify.topic,
        mark=7 if lesson_to_modify.mark != 7 else 8,
        day=modified_day,
    )
    logger.info(
        f"Created modified lesson: {modified_lesson.id}, mark={modified_lesson.mark}"
    )

    modified_day.lessons = [modified_lesson]
    modified_schedule = Schedule(
        id=saved_schedule.id,
        nickname=saved_schedule.nickname,
        days=[modified_day],
    )

    # Test changes are detected
    changes = await repository.get_changes(modified_schedule)

    # Log changes
    logger.info("Changes detected:")
    for day_changes in changes.days:
        for lesson_change in day_changes.lessons:
            if lesson_change.mark_changed:
                logger.info(
                    f"Mark change detected in lesson {lesson_change.lesson_id}: {lesson_change.old_mark} -> {lesson_change.new_mark}"
                )

    # Check for mark changes
    mark_changes = []
    for day_changes in changes.days:
        mark_changes.extend([c for c in day_changes.lessons if c.mark_changed])
    assert len(mark_changes) > 0, "No mark changes detected"

    # Save modified schedule
    await repository.save_schedule(modified_schedule)

    # Load and verify modified schedule
    loaded_modified = await repository.get_schedule_by_id(
        modified_schedule.id, modified_schedule.nickname
    )
    assert loaded_modified is not None

    # Find the modified lesson in the loaded schedule
    found_lesson = None
    for day in loaded_modified.days:
        for lesson in day.lessons:
            if lesson.id == modified_lesson.id:
                found_lesson = lesson
                break
        if found_lesson:
            break

    assert found_lesson is not None, "Modified lesson not found in loaded schedule"
    assert (
        found_lesson.mark == modified_lesson.mark
    ), "Mark was not changed to expected value"


@pytest.mark.asyncio
async def test_get_attachment_path(db_session):
    """Test getting attachment path from repository"""
    repository = ScheduleRepository(db_session)

    # Create test schedule with attachment
    day = SchoolDay(
        id="20240101",
        date=datetime(2024, 1, 1),
        lessons=[],
    )
    schedule = Schedule(
        id="202401",
        nickname="Test Student",
        days=[day],
    )

    lesson = Lesson(
        id="20240101_01_1",
        index=1,
        subject="Test Subject",
        topic="Test Topic",
        day=day,
    )
    day.lessons.append(lesson)

    # Add attachment to lesson
    attachment = lesson.create_topic_attachment(
        filename="test.pdf",
        url="http://test.com/test.pdf",
    )
    lesson.topic_attachments.append(attachment)

    # Save schedule
    await repository.save_schedule(schedule)
    await db_session.flush()

    # Get the attachment ID before testing the path
    attachment_id = await attachment.awaitable_attrs.id

    # Test getting attachment path
    path = repository.get_attachment_path(attachment_id)
    assert path is not None
    assert isinstance(path, Path)
    assert path.name.startswith(attachment_id)
    assert path.name.endswith(".pdf")
    assert "data/attachments" in str(path)

    # Test with non-existent attachment ID
    path = repository.get_attachment_path("nonexistent_id")
    assert path is None


@pytest.mark.asyncio
async def test_multiple_schedules_data_comparison(db_session):
    """Test and compare data from multiple schedule files"""
    repository = ScheduleRepository(db_session)
    strategy = JsonCssExtractionStrategy(JSON_SCHEMA)

    test_files = [
        "test_ekdg_20240212.html",
        "test_ekdg_20241118.html",
        "test_ekdg_20241125.html",
    ]

    results = []

    for filename in test_files:
        # Process each file
        html = load_test_file(filename, base_dir="test_data")
        raw_data = strategy.extract(html=html, url="https://test.com")

        pipeline = create_default_pipeline(nickname="Test Student")
        schedule = pipeline.execute(raw_data)

        # Collect detailed statistics
        total_links = 0
        total_attachments = 0
        attachment_details = []

        for day in schedule.days:
            for lesson in day.lessons:
                # Count topic attachments
                topic_attachments = len(lesson.topic_attachments)
                if topic_attachments > 0:
                    attachment_details.append(
                        f"Lesson {lesson.index} topic: {topic_attachments} attachments"
                    )
                total_attachments += topic_attachments

                if lesson.homework:
                    total_links += len(lesson.homework.links)
                    homework_attachments = len(lesson.homework.attachments)
                    if homework_attachments > 0:
                        attachment_details.append(
                            f"Lesson {lesson.index} homework: "
                            f"{homework_attachments} attachments"
                        )
                    total_attachments += homework_attachments

        # Collect detailed link information
        link_details = []
        for day in schedule.days:
            for lesson in day.lessons:
                if lesson.homework and lesson.homework.links:
                    link_details.append(
                        f"Day {day.date.strftime('%Y-%m-%d')} Lesson {lesson.index}: "
                        f"{len(lesson.homework.links)} links - "
                        f"{[link.original_url for link in lesson.homework.links]}"
                    )

        results.append(
            {
                "filename": filename,
                "days": len(schedule.days),
                "links": total_links,
                "attachments": total_attachments,
                "attachment_details": attachment_details,
                "link_details": link_details,
                "schedule": schedule,
            }
        )

        # Save to database to verify data integrity
        await repository.save_schedule(schedule)

    # Print detailed comparison results
    print("\nDetailed Schedule Data Comparison:")
    print("-" * 50)
    for result in results:
        print(f"\nFile: {result['filename']}")
        print(f"Days: {result['days']}")
        print(f"Total Links: {result['links']}")
        print(f"Total Attachments: {result['attachments']}")
        print("Link Details:")
        for detail in result["link_details"]:
            print(f"  {detail}")
        print("Attachment Details:")
        for detail in result["attachment_details"]:
            print(f"  {detail}")

    # Verify basic expectations for all files
    for result in results:
        assert result["days"] > 0, f"No days found in {result['filename']}"
        assert result["links"] >= 0, f"Invalid link count in {result['filename']}"
        assert (
            result["attachments"] >= 0
        ), f"Invalid attachment count in {result['filename']}"

    # Specific assertions for test_ekdg_20240212.html
    feb_result = next(r for r in results if r["filename"] == "test_ekdg_20240212.html")
    assert (
        feb_result["links"] == 1
    ), "Expected exactly 1 link (typingclub.com) in February schedule"
    assert (
        feb_result["attachments"] == 5
    ), "Expected exactly 5 attachments (.pptx, .docx, .ppt files) in February schedule"

    # Specific assertions for test_ekdg_20241118.html
    nov18_result = next(
        r for r in results if r["filename"] == "test_ekdg_20241118.html"
    )
    assert nov18_result["links"] == 0, "Expected no links in November 18th schedule"
    assert (
        nov18_result["attachments"] == 9
    ), "Expected exactly 9 attachments in November 18th schedule"

    # Specific assertions for test_ekdg_20241125.html
    nov25_result = next(
        r for r in results if r["filename"] == "test_ekdg_20241125.html"
    )
    assert (
        nov25_result["links"] == 1
    ), "Expected exactly 1 link in November 25th schedule"
    assert (
        nov25_result["attachments"] == 12
    ), "Expected exactly 12 attachments in November 25th schedule"
