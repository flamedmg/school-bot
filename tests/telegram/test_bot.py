from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fakeredis.aioredis import FakeRedis
from telethon import TelegramClient, events, Button

from src.database.kvstore import KeyValueStore
from src.telegram.bot import (
    send_welcome_message,
    setup_handlers,
    MENU_OPTIONS,
    display_menu,
    handle_callback,
    log_user_selection,
)


@pytest.fixture
async def redis():
    """Fixture for fake Redis connection."""
    fake_redis = FakeRedis()
    yield fake_redis
    await fake_redis.flushdb()
    await fake_redis.aclose()  # Using aclose() instead of close()


@pytest.fixture
def kv_store(redis):
    """Fixture for KeyValueStore instance."""
    return KeyValueStore(redis)


@pytest.fixture
def mock_bot():
    """Fixture for mocked TelegramClient."""
    bot = AsyncMock(spec=TelegramClient)
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_event():
    """Fixture for mocked Telethon event."""
    event = AsyncMock()
    event.respond = AsyncMock()
    event.answer = AsyncMock()
    event.sender_id = 12345
    return event


@pytest.fixture
def mock_dependencies(kv_store):
    """Fixture to mock Dependencies.get_kvstore."""
    with patch("src.telegram.bot.get_kvstore", return_value=kv_store):
        yield


@pytest.mark.usefixtures("mock_dependencies")
class TestTelegramBot:
    async def test_send_welcome_message_first_time(self, mock_bot, kv_store):
        """Test sending welcome message for the first time."""
        chat_id = 123456
        await send_welcome_message(mock_bot, chat_id)

        mock_bot.send_message.assert_called_once()
        assert await kv_store.get_last_greeting_time() is not None

    async def test_send_welcome_message_same_day(self, mock_bot, kv_store):
        """Test skipping welcome message when already sent today."""
        chat_id = 123456
        now = datetime.now().timestamp()
        await kv_store.set_last_greeting_time(now)

        await send_welcome_message(mock_bot, chat_id)

        mock_bot.send_message.assert_not_called()
        stored_time = await kv_store.get_last_greeting_time()
        assert stored_time == now  # Time should not be updated

    async def test_send_welcome_message_next_day(self, mock_bot, kv_store):
        """Test sending welcome message when last sent yesterday."""
        chat_id = 123456
        yesterday = (datetime.now() - timedelta(days=1)).timestamp()
        await kv_store.set_last_greeting_time(yesterday)

        await send_welcome_message(mock_bot, chat_id)

        mock_bot.send_message.assert_called_once()
        new_time = await kv_store.get_last_greeting_time()
        assert new_time > yesterday

    async def test_send_welcome_message_invalid_chat(self, mock_bot, kv_store):
        """Test handling invalid chat ID."""
        chat_id = -1
        mock_bot.send_message.side_effect = Exception("Invalid chat ID")

        await send_welcome_message(mock_bot, chat_id)

        mock_bot.send_message.assert_called_once()
        assert (
            await kv_store.get_last_greeting_time() is None
        )  # Should not set timestamp on error

    async def test_display_menu(self, mock_event):
        """Test menu display with correct buttons."""
        await display_menu(mock_event)

        mock_event.respond.assert_called_once()
        call_args = mock_event.respond.call_args[0]
        assert "Please select an option:" in call_args[0]

        # Verify buttons were passed
        buttons = mock_event.respond.call_args[1]["buttons"]
        assert len(buttons) == len(MENU_OPTIONS)

        # Verify button text matches menu options
        button_texts = [button[0].text for button in buttons]
        assert all(text in button_texts for text in MENU_OPTIONS.values())

    async def test_handle_callback_schedule(self, mock_event):
        """Test callback handling for schedule option."""
        mock_event.data = b"schedule"
        await handle_callback(mock_event)

        assert mock_event.answer.called
        mock_event.respond.assert_called_once()
        response = mock_event.respond.call_args[0][0]
        assert "You selected: 📅 View Schedule" in response
        assert "show you the schedule" in response

    async def test_handle_callback_homework(self, mock_event):
        """Test callback handling for homework option."""
        mock_event.data = b"homework"
        await handle_callback(mock_event)

        assert mock_event.answer.called
        mock_event.respond.assert_called_once()
        response = mock_event.respond.call_args[0][0]
        assert "You selected: 📚 Check Homework" in response
        assert "homework assignments" in response

    async def test_log_user_selection(self, mock_event, caplog):
        """Test user selection logging."""
        user_id = 12345
        selection = "schedule"

        await log_user_selection(user_id, selection)

        assert f"User {user_id} selected: {selection}" in caplog.text

    async def test_setup_handlers(self, mock_bot):
        """Test handler setup."""
        setup_handlers(mock_bot)

        # Verify handlers were registered
        assert mock_bot.on.call_count >= 3  # /menu, /start, and callback handlers

        # Verify patterns for command handlers
        patterns = [
            call.args[0].pattern
            for call in mock_bot.on.call_args_list
            if isinstance(call.args[0], events.NewMessage)
        ]
        assert "/menu" in str(patterns)
        assert "/start" in str(patterns)
