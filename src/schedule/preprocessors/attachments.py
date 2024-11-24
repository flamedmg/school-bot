"""
Attachments Preprocessor

This preprocessor extracts all attachments from homework entries into a simple list of filename/url pairs.
Adds an 'attachments' key to the root level of the data structure.

Modifications:
- Attachments without a filename are now processed, and the filename is extracted from the URL if possible.
- All attachments with a URL are included in the output.
"""

import logging
from typing import Dict, List, Any
from urllib.parse import unquote, urlparse, parse_qs
from pathlib import Path
from .exceptions import PreprocessingError

logger = logging.getLogger(__name__)


def extract_filename_from_url(url: str) -> str:
    """
    Extract filename from URL, handling various URL formats.
    Falls back to a generic name if extraction fails.
    """
    try:
        # Parse and decode URL
        parsed = urlparse(unquote(url))

        # Try to get filename from path
        path = Path(parsed.path)
        if path.name:
            return path.name

        # If no filename found in path, check query parameters
        if parsed.query:
            # Parse query parameters
            query_params = parse_qs(parsed.query)
            # Common query param names for files
            for param in ["filename", "file", "name", "download"]:
                if param in query_params:
                    filenames = query_params[param]
                    if filenames:
                        return unquote(filenames[0])

        # Fall back to "link" + extension if present
        if path.suffix:
            ext = path.suffix
            return f"link{ext}"

        return "link"

    except Exception:
        return "link"


def extract_attachments(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
        else:
            days = data
            wrap_output = False

        total_days = len(days)
        logger.info(f"Processing attachments for {total_days} days")
        all_attachments = []

        for day in days:
            if not isinstance(day, dict):
                raise PreprocessingError(
                    "Failed to extract attachments: Invalid day data type", {"day": day}
                )

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
                            # Parse URL to extract query parameters
                            from urllib.parse import urlparse, parse_qs

                            parsed = urlparse(url)
                            query = parse_qs(parsed.query)

                            # First try to get filename from query parameter
                            if "filename" in query:
                                filename = query["filename"][0]
                            else:
                                # Otherwise get the last part of the path
                                path = parsed.path.rstrip("/")
                                if path:
                                    filename = path.split("/")[-1]
                                else:
                                    filename = "link"

                        all_attachments.append({"filename": filename, "url": url})

        logger.info(f"Successfully processed attachments:")
        logger.info(f"  - {total_lessons} lessons checked")
        logger.info(f"  - {total_homework} homework entries found")
        logger.info(f"  - {total_attachments} attachments extracted")

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
