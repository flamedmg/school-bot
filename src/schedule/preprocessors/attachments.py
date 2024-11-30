"""
Attachments Preprocessor

This preprocessor extracts all attachments from homework entries into a simple list of filename/url pairs.
Adds an 'attachments' key to the root level of the data structure.

Modifications:
- Attachments without a filename are now processed, and the filename is extracted from the URL if possible.
- All attachments with a URL are included in the output.
- Each attachment includes a unique_id generated from schedule_id, subject, lesson number, and day_id.
"""

import re
from loguru import logger
from typing import Dict, List, Any, Optional
from urllib.parse import unquote, urlparse, parse_qs, urljoin
from pathlib import Path
from .exceptions import PreprocessingError


def clean_lesson_number(number: str) -> str:
    """
    Clean lesson number by removing dots and spaces, handling various formats.
    Returns "0" for invalid or empty numbers.
    """
    if not number:
        return "0"

    # Remove dots and spaces
    cleaned = number.replace(".", "").strip()

    # Extract first sequence of digits
    import re

    match = re.search(r"\d+", cleaned)
    if match:
        return match.group()

    return "0"


def extract_filename_from_url(url: str) -> str:
    """Extract filename from URL, handling various URL formats"""
    try:
        parsed = urlparse(unquote(url))
        
        # First check query parameters for filename
        if parsed.query:
            params = parse_qs(parsed.query)
            if "filename" in params and params["filename"]:
                return params["filename"][0]
        
        # Then try to get filename from path
        path = Path(parsed.path)
        if path.name and path.suffix:
            return path.name
        
        # If no extension in path, check if there's a meaningful name
        if path.name and not path.name.startswith(('download', 'get', 'file')):
            return path.name
            
        # Fall back to "link" + extension if present
        if path.suffix:
            return f"link{path.suffix}"
            
        return "link"
    except Exception:
        return "link"


def generate_unique_id(
    schedule_id: str, subject: str, lesson_number: str, day_id: str
) -> str:
    """
    Generate a unique ID for an attachment by combining schedule, subject, lesson, and day information.
    """
    # Clean and normalize the components
    clean_subject = subject.strip().lower()
    # Replace special characters with underscores
    clean_subject = re.sub(r'[^a-z0-9]+', '_', clean_subject)
    # Remove trailing underscores and multiple underscores
    clean_subject = re.sub(r'_+', '_', clean_subject.strip('_'))
    
    clean_lesson = clean_lesson_number(lesson_number)

    # Combine components with underscores
    return f"{schedule_id}_{day_id}_{clean_subject}_{clean_lesson}"


def extract_attachments(
    data: List[Dict[str, Any]], base_url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Extract all attachments from homework entries into a simple list of filename/url pairs.
    Adds an 'attachments' key to the root level of the data structure.
    """
    try:
        if not data:
            logger.info("No data to process")
            return [{"attachments": []}]

        total_days = 0
        total_lessons = 0
        total_homework = 0
        total_attachments = 0

        # Handle case where input is a list containing a single dictionary with 'days' key
        if len(data) == 1 and isinstance(data[0], dict) and "days" in data[0]:
            days = data[0]["days"]
            wrap_output = True
            # Get schedule_id from the first day's date
            if days and isinstance(days[0], dict) and "date" in days[0]:
                first_date = days[0]["date"]
                schedule_id = first_date.strftime("%Y%W")  # Get year and week number
                logger.debug(
                    f"First day date: {first_date}, schedule_id: {schedule_id}"
                )
            else:
                schedule_id = ""
        else:
            days = data
            wrap_output = False
            schedule_id = ""

        total_days = len(days)
        logger.info(f"Processing attachments for {total_days} days")
        all_attachments = []

        for day in days:
            if not isinstance(day, dict):
                raise PreprocessingError(
                    "Failed to extract attachments: Invalid day data type", {"day": day}
                )

            # Debug log day structure
            logger.debug("Day structure:")
            logger.debug(day)

            # Get day's date and format as YYYYMMDD for unique_id
            day_date = day.get("date")
            if day_date:
                day_id = day_date.strftime("%Y%m%d")
                logger.debug(f"Day date: {day_date}, day_id: {day_id}")
            else:
                day_id = ""
                logger.warning("No date found in day object")

            lessons = day.get("lessons", [])
            if not isinstance(lessons, list):
                raise PreprocessingError(
                    "Failed to extract attachments: Invalid lessons data type",
                    {"lessons": lessons},
                )

            total_lessons += len(lessons)
            for lesson in lessons:
                if not isinstance(lesson, dict):
                    raise PreprocessingError(
                        "Failed to extract attachments: Invalid lesson data type",
                        {"lesson": lesson},
                    )

                homework = lesson.get("homework")
                if homework is not None and not isinstance(homework, dict):
                    raise PreprocessingError(
                        "Failed to extract attachments: Invalid homework data type",
                        {"homework": homework},
                    )

                if not homework:
                    continue

                total_homework += 1
                attachments = homework.get("attachments", [])
                if not isinstance(attachments, list):
                    raise PreprocessingError(
                        "Failed to extract attachments: Invalid attachments data type",
                        {"attachments": attachments},
                    )

                # Get lesson details
                subject = lesson.get("subject", "")
                lesson_number = clean_lesson_number(lesson.get("number", ""))
                logger.debug(f"Using lesson number: {lesson_number}")

                for attachment in attachments:
                    if not isinstance(attachment, dict):
                        raise PreprocessingError(
                            "Failed to extract attachments: Invalid attachment data type",
                            {"attachment": attachment},
                        )

                    if "url" in attachment:
                        total_attachments += 1
                        url = attachment["url"]
                        filename = attachment.get("filename")

                        # If filename is missing, try to extract it from URL
                        if not filename:
                            filename = extract_filename_from_url(url)

                        # Convert relative URL to absolute URL if base_url is provided
                        if base_url:
                            url = urljoin(base_url, url)

                        # Generate unique ID
                        unique_id = generate_unique_id(
                            schedule_id, subject, lesson_number, day_id
                        )

                        # Add attachment with context
                        attachment_data = {
                            "filename": filename,
                            "url": url,
                            "unique_id": unique_id,
                        }
                        logger.debug(f"Adding attachment: {attachment_data}")
                        all_attachments.append(attachment_data)

        logger.info(f"Successfully processed attachments:")
        logger.info(f"  - {total_lessons} lessons checked")
        logger.info(f"  - {total_homework} homework entries found")
        logger.info(f"  - {total_attachments} attachments extracted")
        logger.debug("All attachments:")
        for att in all_attachments:
            logger.debug(att)

        # Create output structure
        result = data[0].copy() if wrap_output else {"days": days}
        result["attachments"] = all_attachments
        return [result]

    except Exception as e:
        if isinstance(e, PreprocessingError):
            raise
        raise PreprocessingError(
            f"Failed to extract attachments: {str(e)}", {"data": data}
        )
