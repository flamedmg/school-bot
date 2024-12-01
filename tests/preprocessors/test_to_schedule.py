from datetime import datetime, UTC

import pytest

from src.database.models import AnnouncementType
from src.schedule.preprocessors.to_schedule import to_schedule


def test_to_schedule_basic():
    """Test basic conversion of pipeline data to database models"""
    input_data = {
        "days": [
            {
                "date": datetime(2024, 1, 15, tzinfo=UTC),
                "lessons": [
                    {
                        "index": 1,
                        "subject": "Math",
                        "room": "210",
                        "topic": "Test topic",
                        "mark": 9,
                        "homework": {
                            "text": "Test homework",
                            "links": [
                                {
                                    "original_url": "http://test.com",
                                    "destination_url": "http://dest.com",
                                }
                            ],
                            "attachments": [
                                {
                                    "filename": "test.pdf",
                                    "url": "http://test.com/test.pdf",
                                }
                            ],
                        },
                    }
                ],
                "announcements": [
                    {
                        "type": AnnouncementType.BEHAVIOR,
                        "behavior_type": "Good",
                        "description": "Test description",
                        "rating": "positive",
                        "subject": "Math",
                    }
                ],
            }
        ],
        "attachments": [
            {
                "filename": "schedule.pdf",
                "url": "http://test.com/schedule.pdf",
            }
        ],
    }

    schedule = to_schedule(input_data, nickname="Test Student")

    # Verify schedule
    assert schedule.nickname == "Test Student"
    assert schedule.id == "202403"  # Week 3 of 2024
    assert len(schedule.days) == 1
    assert len(schedule.attachments) == 1

    # Verify day
    day = schedule.days[0]
    assert day.id == "20240115"
    assert day.date == datetime(2024, 1, 15, tzinfo=UTC)
    assert len(day.lessons) == 1
    assert len(day.announcements) == 1

    # Verify lesson
    lesson = day.lessons[0]
    assert lesson.id == "20240115_15_1"  # YYYYMMDD_DD_index
    assert lesson.subject == "Math"
    assert lesson.room == "210"
    assert lesson.topic == "Test topic"
    assert lesson.mark == 9
    assert lesson.day_id == day.id

    # Verify homework
    homework = lesson.homework
    assert homework is not None
    assert homework.text == "Test homework"
    assert len(homework.links) == 1
    assert len(homework.attachments) == 1

    # Verify homework link
    link = homework.links[0]
    assert link.original_url == "http://test.com"
    assert link.destination_url == "http://dest.com"
    assert link.id.startswith(lesson.id)  # Should include lesson ID

    # Verify homework attachment
    attachment = homework.attachments[0]
    assert attachment.filename == "test.pdf"
    assert attachment.url == "http://test.com/test.pdf"
    assert attachment.id.startswith(homework.id)  # Should include homework ID

    # Verify announcement
    announcement = day.announcements[0]
    assert announcement.type == AnnouncementType.BEHAVIOR
    assert announcement.behavior_type == "Good"
    assert announcement.description == "Test description"
    assert announcement.rating == "positive"
    assert announcement.subject == "Math"
    assert announcement.id.startswith(day.id)
    assert "behavior" in announcement.id  # Should include type

    # Verify schedule attachment
    schedule_attachment = schedule.attachments[0]
    assert schedule_attachment.filename == "schedule.pdf"
    assert schedule_attachment.url == "http://test.com/schedule.pdf"
    assert schedule_attachment.id.startswith(schedule.id)


def test_to_schedule_empty_data():
    """Test conversion with minimal data"""
    input_data = {
        "days": [
            {
                "date": datetime(2024, 1, 15, tzinfo=UTC),
                "lessons": [],
                "announcements": [],
            }
        ],
        "attachments": [],
    }

    schedule = to_schedule(input_data, nickname="Test Student")
    assert schedule.nickname == "Test Student"
    assert schedule.id == "202403"
    assert len(schedule.days) == 1
    assert len(schedule.attachments) == 0

    day = schedule.days[0]
    assert day.id == "20240115"
    assert len(day.lessons) == 0
    assert len(day.announcements) == 0


def test_to_schedule_general_announcement():
    """Test conversion with general announcement"""
    input_data = {
        "days": [
            {
                "date": datetime(2024, 1, 15, tzinfo=UTC),
                "lessons": [],
                "announcements": [
                    {
                        "type": AnnouncementType.GENERAL,
                        "text": "School meeting tomorrow",
                    }
                ],
            }
        ],
        "attachments": [],
    }

    schedule = to_schedule(input_data, nickname="Test Student")
    announcement = schedule.days[0].announcements[0]
    assert announcement.type == AnnouncementType.GENERAL
    assert announcement.text == "School meeting tomorrow"
    assert "general" in announcement.id  # Should include type


def test_to_schedule_lesson_without_homework():
    """Test conversion of lesson without homework"""
    input_data = {
        "days": [
            {
                "date": datetime(2024, 1, 15, tzinfo=UTC),
                "lessons": [
                    {
                        "index": 1,
                        "subject": "Math",
                        "room": "210",
                    }
                ],
                "announcements": [],
            }
        ],
        "attachments": [],
    }

    schedule = to_schedule(input_data, nickname="Test Student")
    lesson = schedule.days[0].lessons[0]
    assert lesson.homework is None
    assert lesson.topic is None
    assert lesson.mark is None
