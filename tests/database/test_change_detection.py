from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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


@pytest.fixture
def repository(db_session):
    """Create a repository instance"""
    return ScheduleRepository(db_session)


@pytest.fixture
def sample_date():
    """Create a sample date"""
    return datetime(2024, 1, 1)


@pytest.fixture
def make_lesson():
    """Factory to create lessons with proper parent references"""

    def _make_lesson(index, subject, mark=None, day=None, room="101"):
        # Create id based on day and index
        day_id = day.id if day else "20240101"
        day_num = day.date.strftime("%d") if day else "01"
        id = f"{day_id}_{day_num}_{index}"

        lesson = Lesson(
            id=id,
            index=index,
            subject=subject,
            mark=mark,
            room=room,
            day=day,
        )
        return lesson

    return _make_lesson


@pytest.fixture
def make_school_day():
    """Factory to create school days"""

    def _make_school_day(date, lessons=None, announcements=None):
        day = SchoolDay(
            id=date.strftime("%Y%m%d"),
            date=date,
            lessons=lessons or [],
            announcements=announcements or [],
        )
        return day

    return _make_school_day


@pytest.fixture
def make_announcement():
    """Factory to create announcements"""

    def _make_announcement(
        type,
        text=None,
        behavior_type=None,
        description=None,
        rating=None,
        subject=None,
        day=None,
    ):
        # Create id based on day and type
        day_id = day.id if day else "20240101"
        day_num = day.date.strftime("%d") if day else "01"

        # Generate hash from content
        content = f"{type.value}:{text or ''}:{behavior_type or ''}:{description or ''}"
        content_hash = f"{''.join(c for c in content if c.isalnum())[:6]}"
        id = f"{day_id}_{day_num}_{type.value}_{content_hash}"

        if type == AnnouncementType.BEHAVIOR:
            # Ensure all required fields are present for behavior announcements
            announcement = Announcement(
                id=id,
                type=type,
                text=text,
                behavior_type=behavior_type or "Good",
                description=description or "Active participation",
                rating=rating or "positive",
                subject=subject or "Math",
                day=day,
            )
        else:
            # For general announcements, only text is required
            announcement = Announcement(
                id=id,
                type=type,
                text=text or "General announcement",
                behavior_type=behavior_type,
                description=description,
                rating=rating,
                subject=subject,
                day=day,
            )
        return announcement

    return _make_announcement


@pytest.fixture
def make_schedule():
    """Factory to create schedules"""

    def _make_schedule(days, nickname="test_student"):
        # Get first day to generate schedule id
        first_day = days[0] if days else None
        schedule_id = first_day.id[:6] if first_day else "202401"

        schedule = Schedule(
            id=schedule_id,
            days=days,
            nickname=nickname,
        )
        # Set schedule reference for days
        for day in days:
            day.schedule = schedule
        return schedule

    return _make_schedule


@pytest.mark.asyncio
async def test_detect_lesson_order_change(
    repository, make_lesson, make_school_day, make_schedule, sample_date
):
    """Test detection of lesson order changes"""
    # Create initial schedule with ordered lessons
    day = make_school_day(date=sample_date)
    lesson1 = make_lesson(index=1, subject="Math", day=day)
    lesson2 = make_lesson(index=2, subject="Physics", day=day)
    day.lessons = [lesson1, lesson2]
    initial_schedule = make_schedule(days=[day])

    # Save initial schedule
    await repository.save_schedule(initial_schedule)

    # Create modified schedule with reversed lesson order
    modified_day = make_school_day(date=sample_date)
    modified_lesson1 = make_lesson(index=1, subject="Physics", day=modified_day)
    modified_lesson2 = make_lesson(index=2, subject="Math", day=modified_day)
    modified_day.lessons = [modified_lesson1, modified_lesson2]
    modified_schedule = make_schedule(days=[modified_day])

    # Check changes
    changes = await repository.get_changes(modified_schedule)
    assert len(changes.days) == 1
    day_changes = changes.days[0]
    print(day_changes)
    order_changes = [c for c in day_changes.lessons if c.order_changed]
    assert len(order_changes) == 1


@pytest.mark.asyncio
async def test_detect_mark_changes(
    repository, make_lesson, make_school_day, make_schedule, sample_date
):
    """Test detection of mark changes"""
    # Create initial schedule with a mark
    day = make_school_day(date=sample_date)
    lesson = make_lesson(index=1, subject="Math", mark=8, day=day, room="101")
    day.lessons = [lesson]
    initial_schedule = make_schedule(days=[day])

    # Save initial schedule
    await repository.save_schedule(initial_schedule)

    # Create modified schedule with changed mark
    modified_day = make_school_day(date=sample_date)
    modified_lesson = make_lesson(
        index=1, subject="Math", mark=9, day=modified_day, room="101"
    )
    modified_day.lessons = [modified_lesson]
    modified_schedule = make_schedule(days=[modified_day])

    # Check changes
    changes = await repository.get_changes(modified_schedule)
    assert len(changes.days) == 1
    day_changes = changes.days[0]
    # We should only see mark changes, not order changes
    mark_changes = [c for c in day_changes.lessons if c.mark_changed]
    assert len(mark_changes) == 1
    assert mark_changes[0].old_mark == 8
    assert mark_changes[0].new_mark == 9


@pytest.mark.asyncio
async def test_detect_subject_changes(
    repository, make_lesson, make_school_day, make_schedule, sample_date
):
    """Test detection of subject changes"""
    # Create initial schedule
    day = make_school_day(date=sample_date)
    lesson = make_lesson(index=1, subject="Math", day=day, room="101")
    day.lessons = [lesson]
    initial_schedule = make_schedule(days=[day])

    # Save initial schedule
    await repository.save_schedule(initial_schedule)

    # Create modified schedule with changed subject
    modified_day = make_school_day(date=sample_date)
    modified_lesson = make_lesson(
        index=1, subject="Advanced Math", day=modified_day, room="101"
    )
    modified_day.lessons = [modified_lesson]
    modified_schedule = make_schedule(days=[modified_day])

    # Check changes
    changes = await repository.get_changes(modified_schedule)
    assert len(changes.days) == 1
    day_changes = changes.days[0]
    subject_changes = [c for c in day_changes.lessons if c.subject_changed]
    assert len(subject_changes) == 1
    assert subject_changes[0].old_subject == "Math"
    assert subject_changes[0].new_subject == "Advanced Math"


@pytest.mark.asyncio
async def test_detect_announcement_changes(
    repository, make_announcement, make_school_day, make_schedule, sample_date
):
    """Test detection of announcement changes"""
    # Create initial schedule with an announcement
    day = make_school_day(date=sample_date)
    announcement = make_announcement(
        type=AnnouncementType.BEHAVIOR,
        behavior_type="Good",
        description="Active participation",
        rating="positive",
        subject="Math",
        day=day,
    )
    day.announcements = [announcement]
    initial_schedule = make_schedule(days=[day])

    # Save initial schedule
    await repository.save_schedule(initial_schedule)

    # Create modified schedule with a different announcement
    modified_day = make_school_day(date=sample_date)
    new_announcement = make_announcement(
        type=AnnouncementType.GENERAL, text="School closed tomorrow", day=modified_day
    )
    modified_day.announcements = [new_announcement]
    modified_schedule = make_schedule(days=[modified_day])

    # Check changes
    changes = await repository.get_changes(modified_schedule)
    assert len(changes.days) == 1
    day_changes = changes.days[0]

    added = [a for a in day_changes.announcements if a.type == ChangeType.ADDED]
    removed = [a for a in day_changes.announcements if a.type == ChangeType.REMOVED]

    assert len(added) == 1
    assert len(removed) == 1
    assert added[0].new_type == AnnouncementType.GENERAL
    assert added[0].new_text == "School closed tomorrow"
    assert removed[0].old_type == AnnouncementType.BEHAVIOR

    # Verify the specific announcements
    assert removed[0].announcement_id == announcement.id
    assert added[0].announcement_id == new_announcement.id

    # Verify removed announcement details
    assert removed[0].announcement_id == announcement.id
    assert removed[0].old_type == AnnouncementType.BEHAVIOR
    assert removed[0].old_text == "Active participation"


@pytest.mark.asyncio
async def test_detect_multiple_changes(
    repository,
    make_lesson,
    make_announcement,
    make_school_day,
    make_schedule,
    sample_date,
):
    """Test detection of multiple types of changes simultaneously"""
    # Create initial schedule
    day = make_school_day(date=sample_date)
    lesson = make_lesson(index=1, subject="Math", mark=8, day=day, room="101")
    announcement = make_announcement(
        type=AnnouncementType.BEHAVIOR,
        behavior_type="Good",
        description="Active participation",
        rating="positive",
        subject="Math",
        day=day,
    )
    day.lessons = [lesson]
    day.announcements = [announcement]
    initial_schedule = make_schedule(days=[day])

    # Save initial schedule
    await repository.save_schedule(initial_schedule)

    # Create modified schedule with multiple changes
    modified_day = make_school_day(date=sample_date)
    modified_lesson = make_lesson(
        index=1, subject="Advanced Math", mark=9, day=modified_day, room="101"
    )
    modified_day.lessons = [modified_lesson]
    modified_schedule = make_schedule(days=[modified_day])

    # Check changes
    changes = await repository.get_changes(modified_schedule)
    assert len(changes.days) == 1
    day_changes = changes.days[0]

    # Check lesson changes (combining mark and subject changes)
    lesson_changes = [
        c for c in day_changes.lessons if c.mark_changed or c.subject_changed
    ]
    print(lesson_changes)
    assert len(lesson_changes) == 1
    lesson_change = lesson_changes[0]
    assert lesson_change.mark_changed
    assert lesson_change.old_mark == 8
    assert lesson_change.new_mark == 9
    assert lesson_change.subject_changed
    assert lesson_change.old_subject == "Math"
    assert lesson_change.new_subject == "Advanced Math"

    # Check announcement changes
    removed = [a for a in day_changes.announcements if a.type == ChangeType.REMOVED]
    assert len(removed) == 1
    assert removed[0].old_type == AnnouncementType.BEHAVIOR

    # Structure should not have changed
    assert not changes.structure_changed


@pytest.mark.asyncio
async def test_detect_announcement_removal(
    repository, make_announcement, make_school_day, make_schedule, sample_date
):
    """Test detection of announcement removal"""
    # Create initial schedule with two announcements
    day = make_school_day(date=sample_date)
    announcement1 = make_announcement(
        type=AnnouncementType.BEHAVIOR,
        behavior_type="Good",
        description="Active participation",
        rating="positive",
        subject="Math",
        day=day,
    )
    announcement2 = make_announcement(
        type=AnnouncementType.GENERAL,
        text="School meeting tomorrow",
        day=day,
    )
    day.announcements = [announcement1, announcement2]
    initial_schedule = make_schedule(days=[day])

    # Save initial schedule
    await repository.save_schedule(initial_schedule)

    # Create modified schedule with one announcement removed
    modified_day = make_school_day(date=sample_date)
    modified_announcement = make_announcement(
        type=AnnouncementType.BEHAVIOR,
        behavior_type="Good",
        description="Active participation",
        rating="positive",
        subject="Math",
        day=modified_day,
    )
    modified_day.announcements = [modified_announcement]
    modified_schedule = make_schedule(days=[modified_day])

    # Check changes
    changes = await repository.get_changes(modified_schedule)
    assert len(changes.days) == 1
    day_changes = changes.days[0]
    removed = [a for a in day_changes.announcements if a.type == ChangeType.REMOVED]
    assert len(removed) == 1
    assert removed[0].announcement_id == announcement2.id
