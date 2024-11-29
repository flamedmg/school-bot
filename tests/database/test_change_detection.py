import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database.models import Base
from src.database.repository import ScheduleRepository
from src.schedule.schema import (
    Schedule,
    SchoolDay,
    Lesson,
    Announcement,
    AnnouncementType,
)


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
        # Create unique_id based on day and index
        day_id = day.date.strftime("%Y%m%d") if day else "20240101"
        unique_id = f"{day_id}_{index}"

        lesson = Lesson(
            unique_id=unique_id,
            index=index,
            subject=subject,
            mark=mark,
            room=room,
        )
        if day:
            lesson._day = day
        return lesson

    return _make_lesson


@pytest.fixture
def make_school_day():
    """Factory to create school days"""

    def _make_school_day(date, lessons=None, announcements=None):
        day = SchoolDay(
            date=date,
            lessons=lessons or [],
            announcements=announcements or [],
        )
        # Set parent references and ensure unique IDs
        for lesson in day.lessons:
            lesson._day = day
            if not lesson.unique_id:
                lesson.unique_id = f"{date.strftime('%Y%m%d')}_{lesson.index}"
        for announcement in day.announcements:
            announcement._day = day
            if not announcement.unique_id:
                announcement.unique_id = (
                    f"{date.strftime('%Y%m%d')}_{len(day.announcements)}"
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
        # Create unique_id based on day and type
        day_id = day.date.strftime("%Y%m%d") if day else "20240101"
        unique_id = f"{day_id}_{type.value}"

        if type == AnnouncementType.BEHAVIOR:
            # Ensure all required fields are present for behavior announcements
            announcement = Announcement(
                unique_id=unique_id,
                type=type,
                text=text,
                behavior_type=behavior_type or "Good",
                description=description or "Active participation",
                rating=rating or "positive",
                subject=subject or "Math",
            )
        else:
            # For general announcements, only text is required
            announcement = Announcement(
                unique_id=unique_id,
                type=type,
                text=text or "General announcement",
                behavior_type=behavior_type,
                description=description,
                rating=rating,
                subject=subject,
            )
        if day:
            announcement._day = day
        return announcement

    return _make_announcement


@pytest.fixture
def make_schedule():
    """Factory to create schedules"""

    def _make_schedule(days, nickname="test_student"):
        schedule = Schedule(
            days=days,
            nickname=nickname,
        )
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
    modified_lesson1 = make_lesson(index=1, subject="Math", day=modified_day)
    modified_lesson2 = make_lesson(index=2, subject="Physics", day=modified_day)
    modified_day.lessons = [modified_lesson2, modified_lesson1]
    modified_schedule = make_schedule(days=[modified_day])

    # Check changes
    changes = await repository.get_changes(modified_schedule)
    assert changes["lessons_changed"] is True


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
    assert len(changes["marks"]) == 1
    assert changes["marks"][0]["old"] == 8
    assert changes["marks"][0]["new"] == 9


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
    assert len(changes["subjects"]) == 1
    assert changes["subjects"][0]["old"] == "Math"
    assert changes["subjects"][0]["new"] == "Advanced Math"


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
    assert len(changes["announcements"]["added"]) == 1
    assert len(changes["announcements"]["removed"]) == 1


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
    assert len(changes["marks"]) == 1
    assert changes["marks"][0]["old"] == 8
    assert changes["marks"][0]["new"] == 9
    assert len(changes["subjects"]) == 1
    assert changes["subjects"][0]["old"] == "Math"
    assert changes["subjects"][0]["new"] == "Advanced Math"
    assert len(changes["announcements"]["removed"]) == 1
    assert not changes["lessons_changed"]
