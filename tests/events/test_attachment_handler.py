import pytest
from unittest.mock import AsyncMock, patch
from src.events.attachment_handler import handle_attachment
from src.events.types import AttachmentEvent
import logging


@pytest.mark.asyncio
async def test_handle_attachment_downloads_file(tmp_path, monkeypatch):
    # Arrange
    event = AttachmentEvent(
        student_nickname="TestStudent",
        filename="test_file.pdf",
        url="https://example.com/test_file.pdf",
        cookies={"sessionid": "fake-session-id"},
        unique_id="202415_testlesson_testday",
    )

    # Change the current working directory to tmp_path
    monkeypatch.chdir(tmp_path)

    # Mock aiohttp.ClientSession to avoid actual HTTP requests
    class MockResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            pass

        async def read(self):
            return b"Test file content"

        async def text(self):
            return "Mock response text"

    class MockClientSession:
        def __init__(self, *args, **kwargs):
            self.cookies = kwargs.get("cookies", {})

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            pass

        def get(self, url, **kwargs):
            # Note: Not async here - returns the MockResponse directly
            return MockResponse()

    # Patch aiohttp.ClientSession
    with patch("aiohttp.ClientSession", new=MockClientSession):
        # Use standard logging logger
        logger = logging.getLogger("test_attachment_handler")

        # Act
        await handle_attachment(event=event, logger=logger)

        # Construct the expected file path
        expected_file_path = (
            tmp_path
            / "data"
            / "attachments"
            / "202415"
            / f"{event.unique_id}_{event.filename}"
        )

        # Assert
        assert expected_file_path.exists(), "File was not downloaded"
        with expected_file_path.open("rb") as f:
            content = f.read()
        assert content == b"Test file content", "Downloaded content does not match"
