import pytest
from datetime import datetime, timedelta
from fakeredis.aioredis import FakeRedis
from src.database.kvstore import KeyValueStore, should_show_greeting


@pytest.fixture
async def redis():
    """Fixture for fake Redis connection."""
    fake_redis = FakeRedis()
    yield fake_redis
    await fake_redis.flushdb()  # Clean up after tests
    await fake_redis.aclose()  # Using aclose() instead of close()


@pytest.fixture
def kv_store(redis):
    """Fixture for KeyValueStore instance."""
    return KeyValueStore(redis)


async def test_set_and_get(kv_store):
    """Test basic set and get operations."""
    await kv_store.set("test_key", "test_value")
    result = await kv_store.get("test_key")
    assert result == "test_value"


async def test_key_prefix(kv_store, redis):
    """Test that keys are properly prefixed."""
    await kv_store.set("test_key", "test_value")
    # Check that the key is stored with prefix in Redis
    raw_value = await redis.get("kvstore:test_key")
    assert raw_value.decode("utf-8") == "test_value"


async def test_get_nonexistent_key(kv_store):
    """Test getting a key that doesn't exist."""
    result = await kv_store.get("nonexistent")
    assert result is None


async def test_greeting_timestamp(kv_store):
    """Test setting and getting greeting timestamp."""
    now = datetime.now().timestamp()
    await kv_store.set_last_greeting_time(now)
    result = await kv_store.get_last_greeting_time()
    assert result == now


@pytest.mark.parametrize(
    "last_greeting,expected",
    [
        (None, True),  # No previous greeting
        (datetime.now().timestamp(), False),  # Greeting today
        ((datetime.now() - timedelta(days=1)).timestamp(), True),  # Greeting yesterday
        ((datetime.now() - timedelta(days=7)).timestamp(), True),  # Greeting last week
    ],
)
async def test_should_show_greeting(kv_store, last_greeting, expected):
    """Test should_show_greeting with various scenarios."""
    if last_greeting is not None:
        await kv_store.set_last_greeting_time(last_greeting)
    assert await should_show_greeting(kv_store) is expected
