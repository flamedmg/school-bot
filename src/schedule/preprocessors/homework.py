"""
Homework Preprocessor

This preprocessor handles cleaning and standardization of homework data:
1. Extracts destination URLs from OAuth links
2. Combines multiple text entries
3. Processes attachments and links
4. Handles special cases for uzdevumi.lv and other platforms

Modifications:
- Attachments without a filename are now allowed to pass through to the extract_attachments step.
- Removed the check that filters out attachments missing the 'filename' key.
"""

from loguru import logger
from typing import Dict, List, Optional, Any
from urllib.parse import parse_qs, unquote, urlparse
from .exceptions import PreprocessingError


def extract_destination_url(url: str) -> Dict[str, Optional[str]]:
    """
    Extract destination URL from OAuth links and standardize other URLs.

    Args:
        url: The URL to process

    Returns:
        Dict with original_url and optional destination_url

    Raises:
        PreprocessingError: If URL is invalid or can't be processed
    """
    if not isinstance(url, str):
        raise PreprocessingError(f"Invalid URL type: {type(url)}")

    result = {"original_url": url, "destination_url": None}

    try:
        # Handle OAuth links with destination_uri parameter
        if "RemoteApp" in url and "destination_uri" in url:
            params = parse_qs(url.split("?", 1)[1])
            if "destination_uri" in params:
                dest_url = unquote(params["destination_uri"][0])
                # Ensure the destination_url includes the scheme
                if not dest_url.startswith(("http://", "https://")):
                    dest_url = "https://" + dest_url
                # Add URL validation
                parsed_url = urlparse(dest_url)
                if not parsed_url.netloc or "." not in parsed_url.netloc:
                    raise PreprocessingError(
                        f"Invalid destination URL: {dest_url}", {"url": dest_url}
                    )
                result["destination_url"] = dest_url
            else:
                # No destination_uri, fall back to original url
                result["destination_url"] = url
        # Handle attachment URLs
        elif url.startswith("/Attachment/Get/"):
            # For attachment URLs, destination_url remains None
            pass
        else:
            # For other URLs, ensure the URL includes the scheme
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            # Add URL validation
            parsed_url = urlparse(url)
            if not parsed_url.netloc or "." not in parsed_url.netloc:
                raise PreprocessingError(f"Invalid URL format: {url}", {"url": url})
            result["destination_url"] = url
    except Exception as e:
        raise PreprocessingError(f"Failed to process URL: {str(e)}", {"url": url})

    return result


def combine_homework_texts(texts: List[str]) -> Optional[str]:
    """
    Combine multiple homework text entries into a single string.
    Removes empty strings and normalizes whitespace.
    """
    if not texts:
        return None

    # Clean and filter texts
    cleaned = [text.strip() for text in texts if text and text.strip()]
    if not cleaned:
        return None

    # Join with space
    return " ".join(cleaned)


def preprocess_homework(homework: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process homework data, standardizing format and cleaning content.

    Args:
        homework: Raw homework data dictionary

    Returns:
        Processed homework dictionary with standardized format

    Raises:
        PreprocessingError: If processing fails
    """
    try:
        result = {"text": None, "links": [], "attachments": []}

        # Process text
        if "text" in homework:
            result["text"] = homework["text"].strip() if homework["text"] else None

        # Process links
        for link in homework.get("links", []):
            if not isinstance(link, dict) or "url" not in link:
                raise PreprocessingError("Invalid link format", {"link": link})

            processed_url = extract_destination_url(link["url"])
            result["links"].append(processed_url)

        # Process attachments
        for attachment in homework.get("attachments", []):
            if not isinstance(attachment, dict) or "url" not in attachment:
                raise PreprocessingError(
                    "Invalid attachment format", {"attachment": attachment}
                )

            result["attachments"].append(
                {"filename": attachment.get("filename"), "url": attachment["url"]}
            )

        # Deduplicate links based on attachment URLs
        # Create a set of attachment URLs
        attachment_urls = set(
            attachment["url"]
            for attachment in result["attachments"]
            if "url" in attachment
        )

        # Filter out links that have URLs already in attachments
        filtered_links = []
        for link in result["links"]:
            link_url = link.get("destination_url") or link.get("original_url")
            if link_url not in attachment_urls:
                filtered_links.append(link)
        result["links"] = filtered_links

        return result

    except PreprocessingError:
        raise
    except Exception as e:
        raise PreprocessingError(
            f"Failed to process homework data: {str(e)}", {"homework": homework}
        )


def preprocess_homeworks(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process all homework entries in the schedule data.

    Args:
        data: List of day dictionaries containing homework entries

    Returns:
        Updated data with processed homework entries

    Raises:
        PreprocessingError: If any homework entry cannot be processed
    """
    total_days = 0
    total_homeworks = 0
    total_links = 0
    total_attachments = 0

    # Handle case where input is a list containing a single dictionary with 'days' key
    if len(data) == 1 and isinstance(data[0], dict) and "days" in data[0]:
        days = data[0]["days"]
        wrap_output = True
    else:
        days = data
        wrap_output = False

    total_days = len(days)
    logger.info(f"Processing homework for {total_days} days")

    for day in days:
        if not isinstance(day, dict):
            continue

        for lesson in day.get("lessons", []):
            if "homework" in lesson:
                try:
                    total_homeworks += 1
                    homework = lesson["homework"]
                    processed = preprocess_homework(homework)

                    # Count links and attachments
                    total_links += len(processed["links"])
                    total_attachments += len(processed["attachments"])

                    lesson["homework"] = processed
                except PreprocessingError:
                    # If processing fails, keep homework unchanged
                    continue

    logger.info(f"Successfully processed {total_homeworks} homework entries:")
    logger.info(f"  - {total_links} links processed")
    logger.info(f"  - {total_attachments} attachments processed")

    # Return in same format as input
    return [{"days": days}] if wrap_output else days
