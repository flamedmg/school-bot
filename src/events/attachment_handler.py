"""
Attachment Handler

This module handles attachment events by downloading files that don't already exist
in the data/attachments/YYYYWW directory.
"""

import os
from datetime import datetime
import aiohttp
from pathlib import Path
from loguru import logger
import traceback
from faststream import Logger

from .types import AttachmentEvent
from .event_types import EventTopics
from .broker import broker
from src.database.repository import ScheduleRepository
from faststream import Depends
from src.events.broker import get_repository


@broker.subscriber(EventTopics.NEW_ATTACHMENT)
async def handle_attachment(
    event: AttachmentEvent,
    logger: Logger,
    repository: ScheduleRepository = Depends(get_repository),
) -> None:
    """
    Handle an attachment event by downloading the file if it doesn't exist.

    Args:
        event: The attachment event containing file details and cookies
        logger: FastStream logger instance
        repository: Repository instance for getting proper file paths
    """
    try:
        # Get proper file path from repository
        file_path = repository.get_attachment_path(
            schedule_id=event.schedule_id,
            subject=event.subject,
            lesson_number=event.lesson_number,
            filename=event.filename,
            day_id=event.day_id,
        )

        # Create parent directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file already exists
        if file_path.exists():
            logger.info(
                f"File {event.filename} already exists at {file_path}, skipping download"
            )
            return

        # Ensure URL is absolute
        url = str(event.url)
        if not url.startswith(("http://", "https://")):
            url = f"https://my.e-klase.lv{url}"

        # Download the file
        try:
            async with aiohttp.ClientSession(cookies=event.cookies) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(file_path, "wb") as f:
                            f.write(content)
                        logger.info(
                            f"Successfully downloaded {event.filename} to {file_path}"
                        )
                    else:
                        error_msg = f"Failed to download {event.filename}: HTTP {response.status}"
                        logger.error(error_msg)
                        logger.error(f"Response text: {await response.text()}")
                        raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error downloading {event.filename}: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
            raise
    except Exception as e:
        error_msg = f"Error handling attachment {event.filename}: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Stack trace:\n{traceback.format_exc()}")
        raise
