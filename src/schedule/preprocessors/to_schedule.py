import hashlib
from datetime import datetime
from typing import Any, Dict, List, Union

from src.database.models import (
    Announcement,
    AnnouncementType,
    Attachment,
    Homework,
    Lesson,
    Link,
    Schedule,
    SchoolDay,
)


def _generate_day_id(date: datetime) -> str:
    """Generate unique ID for a school day (YYYYMMDD format)"""
    return date.strftime("%Y%m%d")


def _generate_schedule_id(first_day: datetime) -> str:
    """Generate unique ID for schedule (YYYYWW format)"""
    year = first_day.isocalendar()[0]
    week = first_day.isocalendar()[1]
    return f"{year}{week:02d}"


def _get_day_number(date: datetime) -> str:
    """Get day number in DD format"""
    return date.strftime("%d")


def _create_attachment(
    data: Dict[str, str],
    schedule_id: str,
    day_id: str,
    parent_type: str,  # 'homework', 'lesson', or 'schedule'
    parent_id: str | None = None,
) -> Attachment:
    """Create an Attachment instance with unique ID"""
    # Generate hash from filename and url
    hash_content = f"{data['filename']}:{data['url']}"
    file_hash = hashlib.md5(hash_content.encode()).hexdigest()[:6]

    # For schedule-level attachments, use schedule_id_hash
    if parent_type == "schedule":
        attachment_id = f"{schedule_id}_{file_hash}"
    # For lesson/homework attachments, use parent_id_hash
    else:
        attachment_id = f"{parent_id}_{file_hash}"

    return Attachment(
        id=attachment_id,
        filename=data["filename"],
        url=data["url"],
        schedule_id=schedule_id if parent_type == "schedule" else None,
    )


def _create_link(
    data: Dict[str, str], schedule_id: str, day_id: str, homework_id: str
) -> Link:
    """Create a Link instance with unique ID"""
    # Generate hash from URLs
    url_content = f"{data['original_url']}:{data.get('destination_url', '')}"
    url_hash = hashlib.md5(url_content.encode()).hexdigest()[:6]

    # Use homework_id_hash as ID
    link_id = f"{homework_id}_{url_hash}"

    return Link(
        id=link_id,
        original_url=data["original_url"],
        destination_url=data.get("destination_url"),
    )


def _create_homework(
    data: Dict[str, Any], schedule_id: str, day_id: str, lesson_id: str
) -> Homework | None:
    """Create a Homework instance with unique ID"""
    if not data:
        return None

    # Generate hash from homework text
    hw_hash = hashlib.md5(str(data.get("text", "")).encode()).hexdigest()[:6]
    homework_id = f"{lesson_id}_{hw_hash}"

    homework = Homework(
        id=homework_id,
        text=data.get("text"),
        links=[],  # Initialize empty, will be populated after homework creation
        attachments=[],  # Initialize empty, will be populated after homework creation
    )

    # Create links and attachments with homework_id
    homework.links = [
        _create_link(link_data, schedule_id, day_id, homework_id)
        for link_data in data.get("links", [])
    ]
    homework.attachments = [
        _create_attachment(att_data, schedule_id, day_id, "homework", homework_id)
        for att_data in data.get("attachments", [])
    ]

    return homework


def _create_lesson(
    data: Dict[str, Any], schedule_id: str, day_id: str, index: int, date: datetime
) -> Lesson:
    """Create a Lesson instance with unique ID"""
    # Format: YYYYMMDD_DD_index
    day_num = _get_day_number(date)
    lesson_id = f"{day_id}_{day_num}_{index}"

    lesson = Lesson(
        id=lesson_id,
        index=data["index"],
        subject=data["subject"],
        room=data.get("room"),
        topic=data.get("topic"),
        topic_attachments=[],  # Initialize empty, will be populated after lesson creation
        homework=None,  # Initialize None, will be set after lesson creation if exists
        mark=data.get("mark"),
        day_id=day_id,
    )

    # Create topic attachments with lesson_id
    lesson.topic_attachments = [
        _create_attachment(att_data, schedule_id, day_id, "lesson", lesson_id)
        for att_data in data.get("topic_attachments", [])
    ]

    # Create homework if exists
    if homework_data := data.get("homework"):
        lesson.homework = _create_homework(
            homework_data, schedule_id, day_id, lesson_id
        )

    return lesson


def _create_announcement(
    data: Dict[str, Any], schedule_id: str, day_id: str, index: int, date: datetime
) -> Announcement:
    """Create an Announcement instance with unique ID"""
    # Format: YYYYMMDD_DD_type_hash
    day_num = _get_day_number(date)

    # Convert string type to enum
    ann_type = AnnouncementType(data["type"])

    # Generate hash from announcement content including subject for uniqueness
    content = (
        str(data.get("text", ""))
        + str(data.get("description", ""))
        + str(data.get("subject", ""))  # Include subject in hash
        + str(index)  # Include index for additional uniqueness
    )
    content_hash = hashlib.md5(content.encode()).hexdigest()[:6]

    announcement_id = f"{day_id}_{day_num}_{ann_type.value}_{content_hash}"

    return Announcement(
        id=announcement_id,
        type=ann_type,
        text=data.get("text"),
        behavior_type=data.get("behavior_type"),
        description=data.get("description"),
        rating=data.get("rating"),
        subject=data.get("subject"),
        day_id=day_id,
    )


def _create_school_day(data: Dict[str, Any], schedule_id: str) -> SchoolDay:
    """Create a SchoolDay instance with unique ID"""
    day_id = _generate_day_id(data["date"])

    day = SchoolDay(
        id=day_id,
        date=data["date"],
        lessons=[],  # Initialize empty, will be populated after day creation
        announcements=[],  # Initialize empty, will be populated after day creation
    )

    # Create lessons with schedule_id and day_id
    day.lessons = [
        _create_lesson(lesson_data, schedule_id, day_id, idx + 1, data["date"])
        for idx, lesson_data in enumerate(data.get("lessons", []))
    ]

    # Create announcements with schedule_id and day_id
    day.announcements = [
        _create_announcement(ann_data, schedule_id, day_id, idx + 1, data["date"])
        for idx, ann_data in enumerate(data.get("announcements", []))
    ]

    return day


def to_schedule(
    data: Union[Dict[str, Any], List[Dict[str, Any]]], nickname: str
) -> Schedule:
    """Convert pipeline data to Schedule database model

    Args:
        data: Raw schedule data, either as a dictionary or list of dictionaries
        nickname: Required nickname for the schedule
    """
    # Handle both dictionary and list input
    schedule_data = data[0] if isinstance(data, list) else data

    schedule_id = _generate_schedule_id(schedule_data["days"][0]["date"])

    # Create schedule first
    schedule = Schedule(
        id=schedule_id,
        nickname=nickname,
        days=[],  # Initialize empty, will be populated after schedule creation
        attachments=[],  # Initialize empty, will be populated after schedule creation
    )

    # Create days with schedule_id
    schedule.days = [
        _create_school_day(day_data, schedule_id) for day_data in schedule_data["days"]
    ]

    # Create schedule attachments with schedule_id
    schedule.attachments = [
        _create_attachment(att_data, schedule_id, schedule.days[0].id, "schedule")
        for att_data in schedule_data.get("attachments", [])
    ]

    return schedule
