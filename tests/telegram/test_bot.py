from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fakeredis.aioredis import FakeRedis
from telethon import TelegramClient

from src.database.kvstore import KeyValueStore
from src.telegram.bot import send_welcome_message


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
