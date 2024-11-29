import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database.enums import ChangeType
from src.database.models import Base
from src.schedule.crawler import JSON_SCHEMA
from src.schedule.preprocess import create_default_pipeline
from src.schedule.schema import (
    Schedule,
    SchoolDay,
    Lesson,
    Homework,
    Announcement,
    AnnouncementType,
)
from src.database.repository import ScheduleRepository
from tests.crawl.utils import load_test_file
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy


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
    pipeline = create_default_pipeline()
    schedule_data = pipeline.execute(raw_data)

    # Add nickname to schedule data
    schedule_data[0]["nickname"] = "Gavrovska Darjana"

    # Convert to Schedule model
    initial_schedule = Schedule(**schedule_data[0])

    # Verify initial schedule data
    assert len(initial_schedule.days) > 0
    first_day = initial_schedule.days[0]
    assert isinstance(first_day.date, datetime)
    assert len(first_day.lessons) > 0

    # Save to database and get it back to verify the save worked
    db_schedule = await repository.save_schedule(initial_schedule)
    saved_schedule = await repository.get_schedule_by_unique_id(
        db_schedule.unique_id, initial_schedule.nickname
    )
    assert saved_schedule is not None
    assert len(saved_schedule.days) == len(initial_schedule.days)

    # Compare days
    for orig_day, saved_day in zip(initial_schedule.days, saved_schedule.days):
        assert orig_day.date == saved_day.date
        assert len(orig_day.lessons) == len(saved_day.lessons)

        # Compare lessons
        for orig_lesson, saved_lesson in zip(orig_day.lessons, saved_day.lessons):
            assert orig_lesson.subject == saved_lesson.subject
            assert orig_lesson.mark == saved_lesson.mark
            assert orig_lesson.room == saved_lesson.room
            assert orig_lesson.topic == saved_lesson.topic

            # Compare homework if exists
            if orig_lesson.homework:
                assert saved_lesson.homework is not None
                assert orig_lesson.homework.text == saved_lesson.homework.text
                assert len(orig_lesson.homework.attachments) == len(
                    saved_lesson.homework.attachments
                )
                assert len(orig_lesson.homework.links) == len(
                    saved_lesson.homework.links
                )

        # Compare announcements
        assert len(orig_day.announcements) == len(saved_day.announcements)
        for orig_ann, saved_ann in zip(orig_day.announcements, saved_day.announcements):
            assert (
                orig_ann.type.value == saved_ann.type.value
            )  # Compare enum values directly
            assert orig_ann.text == saved_ann.text
            assert orig_ann.behavior_type == saved_ann.behavior_type
            assert orig_ann.description == saved_ann.description
            assert orig_ann.rating == saved_ann.rating
            assert orig_ann.subject == saved_ann.subject

    # Now make some changes to test change detection
    # Create a new schedule from pipeline output to simulate newly parsed data
    initial_schedule = Schedule(**schedule_data[0])
    modified_schedule = initial_schedule.model_copy(deep=True)

    # Modify the data to include our changes
    modified_schedule.days[0].lessons[0].mark = 9
    modified_schedule.days[0].lessons[1].subject = "Modified Subject"
    modified_schedule.days[0].announcements.append(
        Announcement(
            type=AnnouncementType.GENERAL,
            text="New test announcement",
            behavior_type=None,
            description=None,
            rating=None,
            subject=None,
        )
    )

    # Test changes are detected
    changes = await repository.get_changes(modified_schedule)

    # Check for mark changes
    mark_changes = []
    for day_changes in changes.days:
        mark_changes.extend([c for c in day_changes.lessons if c.mark_changed])
    assert len(mark_changes) > 0

    # Check for subject changes
    subject_changes = []
    for day_changes in changes.days:
        subject_changes.extend([c for c in day_changes.lessons if c.subject_changed])
    assert len(subject_changes) > 0

    # Check for announcement changes
    announcement_changes = []
    for day_changes in changes.days:
        announcement_changes.extend(
            [c for c in day_changes.announcements if c.type == ChangeType.ADDED]
        )
    assert len(announcement_changes) > 0

    # Save modified schedule
    await repository.save_schedule(modified_schedule)

    # Load and verify modified schedule
    loaded_modified = await repository.get_schedule_by_unique_id(
        modified_schedule.unique_id, modified_schedule.nickname
    )
    assert loaded_modified is not None

    # Verify modifications were saved correctly
    modified_day = next(
        d for d in loaded_modified.days if d.date == modified_schedule.days[0].date
    )
    assert modified_day.lessons[0].mark == 9
    assert modified_day.lessons[1].subject == "Modified Subject"
    assert len(modified_day.announcements) == len(
        modified_schedule.days[0].announcements
    )
    assert any(a.text == "New test announcement" for a in modified_day.announcements)
