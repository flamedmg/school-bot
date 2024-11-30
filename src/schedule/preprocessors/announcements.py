"""
Announcements Preprocessor

This preprocessor handles parsing and structuring of announcements:
1. Handles two types of announcements:
   - Behavior announcements with rating and subject
   - General informational announcements
2. Extracts components like behavior type, description, rating, subject
3. Preserves full text for general announcements
"""

import re

from loguru import logger

from .exceptions import PreprocessingError


def parse_single_announcement(text: str) -> dict[str, str]:
    """Parse a single announcement text into its components."""
    try:
        # Clean the text first - normalize whitespace and remove newlines
        cleaned_text = " ".join(text.strip().split())

        # Try to parse behavior announcement
        behavior_match = re.match(
            r"^(Centīgs|Mērķtiecīgs)(?::\s*|\s+)(.*?)\s*\((pozitīvs|negatīvs)\)",
            cleaned_text,
        )
        if behavior_match:
            behavior_type, description, rating = behavior_match.groups()
            # Extract subject from parentheses after date and before teacher's name
            subject_match = re.search(
                r"\(\d{2}\.\d{2}\.,\s*(.*?),\s*[^,]*\)$", cleaned_text
            )
            subject = subject_match.group(1).strip() if subject_match else None
            return {
                "type": "behavior",
                "behavior_type": behavior_type,
                "description": description.strip(),
                "rating": rating,
                "subject": subject,
            }

        # If not a behavior announcement, treat as general announcement
        return {"type": "general", "text": cleaned_text}

    except Exception as e:
        if isinstance(e, PreprocessingError):
            raise
        raise PreprocessingError(
            f"Failed to process announcement: {str(e)}", {"text": text}
        ) from e


def preprocess_announcements(data: list[dict]) -> list[dict]:
    """
    Process all announcements in the schedule data.
    Parses and structures announcement text into components.
    """
    total_days = 0
    total_announcements = 0
    behavior_announcements = 0
    general_announcements = 0

    # Handle case where input is a list containing a single dictionary with 'days' key
    if len(data) == 1 and isinstance(data[0], dict) and "days" in data[0]:
        days = data[0]["days"]
        wrap_output = True
    else:
        days = data
        wrap_output = False

    total_days = len(days)
    logger.info(f"Processing announcements for {total_days} days")

    for day in days:
        if not isinstance(day, dict):
            continue

        if "announcements" not in day:
            continue

        day_announcements = day["announcements"]
        total_announcements += len(day_announcements)
        processed_announcements = []

        for announcement in day_announcements:
            if not isinstance(announcement, dict) or "text" not in announcement:
                raise PreprocessingError(
                    "Invalid announcement data structure",
                    {"announcement": announcement},
                )

            try:
                parsed = parse_single_announcement(announcement["text"])
                if parsed["type"] == "behavior":
                    behavior_announcements += 1
                else:
                    general_announcements += 1
                processed_announcements.append(parsed)
            except PreprocessingError as e:
                # Re-raise PreprocessingError with more context
                raise PreprocessingError(
                    f"Failed to process announcement: {str(e)}",
                    {"day": day, "announcement": announcement, "original_error": e},
                ) from e

        day["announcements"] = processed_announcements

    logger.info(f"Processed {total_announcements} announcements:")
    logger.info(f"  - {behavior_announcements} behavior announcements")
    logger.info(f"  - {general_announcements} general announcements")

    # Return in same format as input
    return [{"days": days}] if wrap_output else days
