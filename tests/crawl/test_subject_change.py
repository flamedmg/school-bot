import pytest
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.models import Base, Schedule
from src.database.repository import ScheduleRepository
from src.schedule.crawler import JSON_SCHEMA
from src.schedule.preprocess import create_default_pipeline
from tests.crawl.utils import load_test_file


@pytest.fixture
async def engine():
    """Create a fresh in-memory database for each test"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(engine):
    """Create a new database session for each test"""
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest.mark.asyncio
async def test_prevent_incorrect_subject_change(db_session):
    """Test that Balagurchiki is not incorrectly changed to Matemātika F."""

    # Create repository
    repository = ScheduleRepository(db_session)

    # Create pipeline and strategy
    pipeline = create_default_pipeline(
        nickname="test_student", base_url="http://test.com"
    )
    strategy = JsonCssExtractionStrategy(JSON_SCHEMA)

    # Load and process original schedule (with Balaguri)
    original_html = load_test_file("test_subject_change.html", base_dir="test_data")
    raw_data = strategy.extract(html=original_html, url="http://test.com")
    original_schedule = pipeline.execute(raw_data)

    # Verify the original schedule has Balagurchiki
    for day in original_schedule.days:
        for lesson in day.lessons:
            # The subject should be translated to Balagurchiki
            assert (
                lesson.subject == "Balagurchiki"
            ), "Subject should be translated to Balagurchiki"

    # Save original schedule
    await repository.save_schedule(original_schedule)
    await db_session.commit()

    # Create updated schedule - should NOT change Balagurchiki to Matemātika F
    updated_schedule = original_schedule

    # Get changes
    changes = await repository.get_changes(updated_schedule)

    # Verify no subject changes were detected
    subject_changes = []
    for day in changes.days:
        subject_changes.extend([c for c in day.lessons if c.subject_changed])

    assert len(subject_changes) == 0, "Should not detect any subject changes"

    # Verify the subjects are still Balagurchiki
    for day in updated_schedule.days:
        for lesson in day.lessons:
            assert (
                lesson.subject == "Balagurchiki"
            ), "Subject should remain as Balagurchiki"


@pytest.mark.asyncio
async def test_detect_actual_subject_change(db_session):
    """Test that actual subject changes are detected correctly."""

    # Create repository
    repository = ScheduleRepository(db_session)

    # Create pipeline and strategy
    pipeline = create_default_pipeline(
        nickname="test_student", base_url="http://test.com"
    )
    strategy = JsonCssExtractionStrategy(JSON_SCHEMA)

    # Load and process original schedule
    original_html = load_test_file("test_subject_change.html", base_dir="test_data")
    raw_data = strategy.extract(html=original_html, url="http://test.com")
    original_schedule = pipeline.execute(raw_data)

    # Save original schedule
    await repository.save_schedule(original_schedule)
    await db_session.commit()

    # Create updated schedule with actual subject changes
    updated_schedule = Schedule(
        id=original_schedule.id,
        nickname=original_schedule.nickname,
        days=[],
    )
    # Copy days and change subjects
    for day in original_schedule.days:
        updated_day = day.__class__(
            id=day.id,
            date=day.date,
            schedule=updated_schedule,
            lessons=[],
            announcements=day.announcements,
        )
        for lesson in day.lessons:
            updated_lesson = lesson.__class__(
                id=lesson.id,
                index=lesson.index,
                subject=(
                    "Matemātika F"
                    if lesson.subject == "Balagurchiki"
                    else lesson.subject
                ),
                room=lesson.room,
                topic=lesson.topic,
                mark=lesson.mark,
                homework=lesson.homework,
                topic_attachments=lesson.topic_attachments,
                day=updated_day,
            )
            updated_day.lessons.append(updated_lesson)
        updated_schedule.days.append(updated_day)

    # Get changes
    changes = await repository.get_changes(updated_schedule)

    # Verify subject changes were detected
    subject_changes = []
    for day in changes.days:
        subject_changes.extend([c for c in day.lessons if c.subject_changed])

    assert len(subject_changes) == 3, "Should detect subject changes for all three days"

    # Verify each change
    for change in subject_changes:
        assert change.old_subject == "Balagurchiki"
        assert change.new_subject == "Matemātika F"
