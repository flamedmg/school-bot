"""
Lessons Preprocessor

This preprocessor handles cleaning and standardization of lesson data:
1. Converts lesson numbers to integers (as index)
2. Separates subject name from room info
3. Cleans and formats topic text
4. Handles Latvian-specific room codes and formatting
"""

import re
from typing import Dict, Any, Optional, List
from loguru import logger
from .exceptions import PreprocessingError


def clean_subject(subject: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Separate subject name from room number and clean up.
    Removes all content in parentheses and cleans up whitespace.
    """
    if not subject:
        return None, None

    # Remove all content in parentheses (including nested)
    while "(" in subject:
        subject = re.sub(r"\s*\([^()]*\)", "", subject)
    subject = subject.strip()

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
        PreprocessingError: If the input is invalid (empty string, invalid format, or wrong type)
    """
    if number is None:
        return None

    # Check for invalid type
    if not isinstance(number, str):
        raise PreprocessingError(
            f"Invalid lesson number type: expected string or None, got {type(number)}",
            {"number": number},
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

        # Handle topic, topic links, and topic attachments
        if "topic" in result and isinstance(result["topic"], dict):
            topic_data = result["topic"]
            result["topic"] = clean_topic(topic_data.get("text", ""))

            # Handle topic links
            if "links" in topic_data:
                if not "homework" in result:
                    result["homework"] = {"text": None, "links": [], "attachments": []}
                result["homework"]["links"].extend(
                    [
                        {"original_url": link["url"], "destination_url": None}
                        for link in topic_data["links"]
                    ]
                )

            # Handle topic attachments
            if "attachments" in topic_data:
                result["topic_attachments"] = topic_data["attachments"]
        elif "topic" in result:
            result["topic"] = clean_topic(result["topic"])
            result["topic_attachments"] = []

        # Convert number to index if present
        if "number" in result:
            try:
                index = clean_lesson_index(result["number"])
                result["index"] = index
                result.pop("number")
            except PreprocessingError as e:
                raise PreprocessingError(
                    f"Failed to process lesson number: {str(e)}",
                    {"lesson": lesson, "original_error": e},
                )
        # Keep existing index if present
        elif "index" in result:
            pass
        else:
            result["index"] = None

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

    except PreprocessingError:
        raise
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
        used_indices = set()
        highest_index = 0

        # First pass: Process lessons and track indices
        for lesson in lessons:
            try:
                processed = preprocess_lesson(lesson)
                if processed["index"] is not None:
                    used_indices.add(processed["index"])
                    highest_index = max(highest_index, processed["index"])
                processed_day_lessons.append(processed)
                processed_lessons += 1
            except PreprocessingError as e:
                logger.error(f"Error processing lesson: {e}")
                continue

        # Second pass: Fill in missing indices sequentially
        next_index = 1
        for lesson in processed_day_lessons:
            if lesson["index"] is None:
                # Find next available index
                while next_index in used_indices:
                    next_index += 1
                lesson["index"] = next_index
                used_indices.add(next_index)
            next_index = max(next_index + 1, lesson["index"] + 1)

        day["lessons"] = processed_day_lessons

    logger.info(
        f"Successfully processed {processed_lessons} lessons across {total_days} days"
    )

    # Return in same format as input
    return [{"days": days}] if wrap_output else days
