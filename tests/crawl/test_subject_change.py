import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database.models import Base
from src.schedule.crawler import JSON_SCHEMA
from src.schedule.preprocess import create_default_pipeline
from src.database.repository import ScheduleRepository
from src.schedule.schema import Schedule
from src.database.types import ScheduleChanges
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from tests.crawl.utils import load_test_file
from src.schedule.preprocessors.lessons import clean_subject


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
    original_data = pipeline.execute(raw_data)
    original_schedule = Schedule(**original_data[0])

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
    updated_data = original_data.copy()
    updated_schedule = Schedule(**updated_data[0])

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
    original_data = pipeline.execute(raw_data)
    original_schedule = Schedule(**original_data[0])

    # Save original schedule
    await repository.save_schedule(original_schedule)
    await db_session.commit()

    # Create updated schedule with actual subject changes
    updated_data = original_data.copy()
    # Change subject for all three days
    for day in updated_data[0]["days"]:
        for lesson in day["lessons"]:
            if lesson["subject"] == "Balagurchiki":
                lesson["subject"] = "Matemātika F"
    updated_schedule = Schedule(**updated_data[0])

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
