"""Tests for student handler functionality."""

import pytest
from datetime import datetime, time
from unittest.mock import AsyncMock, patch
from src.telegram.handlers.student import display_schedule_options


@pytest.fixture
def mock_event():
    """Fixture for mocked Telethon event."""
    event = AsyncMock()
    event.respond = AsyncMock()
    return event


@pytest.mark.parametrize(
    "current_time,weekday,expected_text",
    [
        # Before noon cases (should show "Today")
        (time(11, 0), 0, "Today"),  # Monday before noon
        (time(11, 0), 4, "Today"),  # Friday before noon
        # After noon cases (should show "Tomorrow" except Friday)
        (time(13, 0), 0, "Tomorrow"),  # Monday after noon
        (time(13, 0), 3, "Tomorrow"),  # Thursday after noon
        # Friday after noon (should show "Monday")
        (time(13, 0), 4, "Monday"),  # Friday after noon
    ],
)
async def test_display_schedule_options(
    mock_event, current_time, weekday, expected_text
):
    """Test schedule options display based on time and day of week."""
    # Mock datetime.now() to return a specific time and weekday
    mock_now = AsyncMock()
    mock_now.time.return_value = current_time
    mock_now.weekday.return_value = weekday

    with patch("src.telegram.handlers.student.datetime") as mock_datetime:
        mock_datetime.now.return_value = mock_now

        await display_schedule_options(mock_event)

        # Verify the response
        mock_event.respond.assert_called_once()
        call_args = mock_event.respond.call_args[1]

        # Extract button text from the response
        buttons = call_args["buttons"]
        day_button_text = buttons[0][0].text

        assert day_button_text == expected_text
        assert (
            buttons[0][1].text == "Next Week"
        )  # Second button should always be "Next Week"
