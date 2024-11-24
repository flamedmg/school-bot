import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


"""
Lessons Preprocessor

This preprocessor handles cleaning and standardization of lesson data:
1. Converts lesson numbers to integers (as index)
2. Separates subject name from room info
3. Cleans and formats topic text
4. Handles Latvian-specific room codes and formatting
"""

import re
from typing import Dict, Any, Optional
from .exceptions import PreprocessingError


def clean_subject(subject: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Separate subject name from room number and clean up.
    """
    if not subject:
        return None, None

    # Remove (I) suffix if present
    subject = subject.replace(" (I)", "").strip()

    # Try to extract numeric room number at the end
    match = re.search(r"(\d{2,3})$", subject)
    if match:
        room = match.group(1)
        subject_name = subject[: -len(room)].strip()
        return subject_name, room

    # Match known room codes
    known_room_codes = ["sz", "mz", "az", "pz"]
    for code in known_room_codes:
        if subject.lower().endswith(code):
            subject_name = subject[: -len(code)].strip()
            room = code
            return subject_name, room

    # If no room found, return subject as is
    return subject, None


def clean_lesson_index(number: Optional[str]) -> Optional[int]:
    """
    Convert lesson number string to integer index.
    Returns None for missing or invalid numbers.

    Raises:
        PreprocessingError: If the input is invalid (empty string or invalid format)
    """
    if number is None:
        return None

    if not isinstance(number, str):
        raise PreprocessingError(
            f"Invalid lesson number type: expected string or None, got {type(number)}"
        )

    # Handle empty string case explicitly
    if not number.strip():
        raise PreprocessingError("Empty lesson number")

    # Handle special case for "·" - it will now get None and be assigned sequentially
    if number.strip() == "·":
        return None

    # Try to extract digits
    cleaned = re.sub(r"[^\d]", "", number)
    if not cleaned:
        raise PreprocessingError(f"Invalid lesson number format: {number}")

    try:
        return int(cleaned)
    except (ValueError, TypeError):
        raise PreprocessingError(f"Invalid lesson number format: {number}")


def clean_topic(topic: str) -> Optional[str]:
    """
    Clean and format topic text.
    - Remove excess whitespace and newlines
    - Preserve Latvian diacritics
    - Maintain SR (sasniedzamais rezultāts) formatting
    """
    if not topic:
        return None

    # Remove newlines and normalize whitespace while preserving content
    cleaned = " ".join(line.strip() for line in topic.splitlines())
    # Normalize multiple spaces into single space
    cleaned = " ".join(cleaned.split())
    return cleaned


def preprocess_lesson(lesson: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single lesson entry"""
    if not isinstance(lesson, dict):
        raise PreprocessingError("Invalid lesson data type", {"lesson": lesson})

    try:
        result = lesson.copy()

        # Convert number to index
        if "number" in result:
            try:
                index = clean_lesson_index(result["number"])
                result["index"] = index  # Add new index field
                del result["number"]  # Remove old number field
            except (ValueError, TypeError, AttributeError):
                raise PreprocessingError(
                    f"Invalid lesson number format", {"lesson": lesson}
                )

        # Clean subject and extract room if needed
        if "subject" in result:
            subject_name, room = clean_subject(result["subject"])
            if subject_name:  # Only update if we got a valid subject name
                result["subject"] = subject_name
                # Only override room if we found one and there isn't already one set
                if room and not result.get("room"):
                    result["room"] = room
                elif not result.get("room"):
                    # If no room was found or set, explicitly set to None
                    result["room"] = None

        # Clean topic
        if "topic" in result:
            result["topic"] = clean_topic(result["topic"])

        # Convert empty room to None
        if "room" in result and not result["room"]:
            result["room"] = None

        return result

    except Exception as e:
        raise PreprocessingError(
            f"Failed to preprocess lesson data: {str(e)}", {"lesson": lesson}
        )


def preprocess_lessons(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process all lessons in the schedule data.
    Cleans and standardizes lesson information.
    """
    total_days = 0
    total_lessons = 0
    processed_lessons = 0

    # Handle case where input is a list containing a single dictionary with 'days' key
    if len(data) == 1 and isinstance(data[0], dict) and "days" in data[0]:
        days = data[0]["days"]
        wrap_output = True
    else:
        days = data
        wrap_output = False

    total_days = len(days)
    logger.info(f"Processing lessons for {total_days} days")

    for day in days:
        if not isinstance(day, dict):
            continue

        lessons = day.get("lessons", [])
        if not isinstance(lessons, list):
            continue

        total_lessons += len(lessons)
        processed_day_lessons = []
        last_valid_index = 0

        # Process all lessons and assign indices
        for lesson in lessons:
            try:
                processed = preprocess_lesson(lesson)
                if "number" in lesson:
                    index = clean_lesson_index(lesson["number"])
                    if index is not None:
                        processed["index"] = index
                        last_valid_index = max(last_valid_index, index)
                    else:
                        # Assign next sequential index after last valid one
                        last_valid_index += 1
                        processed["index"] = last_valid_index
                processed_day_lessons.append(processed)
                processed_lessons += 1
            except PreprocessingError:
                processed_day_lessons.append(lesson)

        # Remove old number field if it exists
        for lesson in processed_day_lessons:
            lesson.pop("number", None)

        # Sort lessons by index to ensure correct order
        processed_day_lessons.sort(key=lambda x: x.get("index", float("inf")))
        day["lessons"] = processed_day_lessons

    logger.info(
        f"Successfully processed {processed_lessons} lessons across {total_days} days"
    )

    # Return in same format as input
    return [{"days": days}] if wrap_output else days
