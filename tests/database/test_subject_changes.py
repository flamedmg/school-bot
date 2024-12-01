from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.models import Base, Lesson, Schedule, SchoolDay
from src.database.repository import ScheduleRepository
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


def create_test_schedule(nickname: str, days_data: list) -> Schedule:
    """Helper to create a test schedule with multiple days"""
    days = []
    for date, subject in days_data:
        # Clean the subject before creating the lesson
        cleaned_subject, room = clean_subject(subject)
        day = SchoolDay(
            id=date.strftime("%Y%m%d"),
            date=date,
            lessons=[],
        )
        lesson = Lesson(
            id=f"{day.id}_6",  # Same index as in production issue
            index=6,
            subject=cleaned_subject,
            room=room or "az",  # Use extracted room or default to "az"
            day=day,
        )
        day.lessons = [lesson]
        days.append(day)

    # Create schedule with id from first day
    schedule_id = days[0].id[:6] if days else "202401"
    schedule = Schedule(
        id=schedule_id,
        nickname=nickname,
        days=days,
    )
    # Set schedule reference for days
    for day in days:
        day.schedule = schedule
    return schedule


@pytest.mark.asyncio
async def test_production_subject_change_issue(db_session):
    """Test that reproduces the production issue with Balagurchiki subject changes."""
    repository = ScheduleRepository(db_session)

    # Create schedule with three days, matching production data
    original_days = [
        (datetime(2024, 4, 7), "Tautas dejas kol. 'Balaguri' (I)"),
        (datetime(2024, 4, 8), "Tautas dejas kol. 'Balaguri' (I)"),
        (datetime(2024, 4, 9), "Tautas dejas kol. 'Balaguri' (I)"),
    ]
    original_schedule = create_test_schedule("test_student", original_days)

    # Verify subjects are cleaned
    for day in original_schedule.days:
        for lesson in day.lessons:
            assert (
                lesson.subject == "Tautas dejas kol. 'Balaguri'"
            ), "Subject should be cleaned"

    # Save original schedule
    await repository.save_schedule(original_schedule)
    await db_session.commit()

    # Create updated schedule with Matemātika F
    updated_days = [
        (datetime(2024, 4, 7), "Matemātika F (F)"),
        (datetime(2024, 4, 8), "Matemātika F (F)"),
        (datetime(2024, 4, 9), "Matemātika F (F)"),
    ]
    updated_schedule = create_test_schedule("test_student", updated_days)

    # Verify updated subjects are cleaned
    for day in updated_schedule.days:
        for lesson in day.lessons:
            assert lesson.subject == "Matemātika F", "Subject should be cleaned"

    # Get changes
    changes = await repository.get_changes(updated_schedule)

    # Verify changes
    subject_changes = []
    for day in changes.days:
        subject_changes.extend([c for c in day.lessons if c.subject_changed])

    # Should detect 3 changes, one for each day
    assert len(subject_changes) == 3, "Should detect changes for all three days"

    # Verify each change shows cleaned subjects
    for change in subject_changes:
        assert (
            change.old_subject == "Tautas dejas kol. 'Balaguri'"
        ), "Old subject should be cleaned"
        assert change.new_subject == "Matemātika F", "New subject should be cleaned"
        assert not change.order_changed, "Order should not be changed"
        assert not change.mark_changed, "Mark should not be changed"


@pytest.mark.asyncio
async def test_subject_change_with_parentheses(db_session):
    """Test that subject changes are detected correctly after cleaning parentheses."""
    repository = ScheduleRepository(db_session)

    # Create schedule with subject including parentheses
    original_days = [(datetime(2024, 4, 7), "Tautas dejas kol. 'Balaguri' (I)")]
    original_schedule = create_test_schedule("test_student", original_days)

    # Verify subject is cleaned
    assert (
        original_schedule.days[0].lessons[0].subject == "Tautas dejas kol. 'Balaguri'"
    )

    # Save original schedule
    await repository.save_schedule(original_schedule)
    await db_session.commit()

    # Create updated schedule with same base subject but different suffix
    updated_days = [(datetime(2024, 4, 7), "Tautas dejas kol. 'Balaguri' (F)")]
    updated_schedule = create_test_schedule("test_student", updated_days)

    # Verify updated subject is cleaned
    assert updated_schedule.days[0].lessons[0].subject == "Tautas dejas kol. 'Balaguri'"

    # Get changes
    changes = await repository.get_changes(updated_schedule)

    # Should not detect changes since the subjects are the same after cleaning
    subject_changes = []
    for day in changes.days:
        subject_changes.extend([c for c in day.lessons if c.subject_changed])

    assert (
        len(subject_changes) == 0
    ), "Should not detect changes when subjects are same after cleaning"
