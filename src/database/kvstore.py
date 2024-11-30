from typing import Optional
from datetime import datetime
from redis.asyncio import Redis


class KeyValueStore:
    """Simple key-value store using Redis for application-wide settings"""

    def __init__(self, redis: Redis):
        self.redis = redis
        self.prefix = "kvstore:"  # Namespace Redis keys to avoid conflicts

    def _key(self, key: str) -> str:
        """Prefix the key to namespace it"""
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Optional[str]:
        """Get a value from the store"""
        result = await self.redis.get(self._key(key))
        return result.decode("utf-8") if result else None

    async def set(self, key: str, value: str):
        """Set a value in the store"""
        await self.redis.set(self._key(key), value)

    # Specific methods for greeting timestamp
    async def get_last_greeting_time(self) -> Optional[float]:
        """Get timestamp of last greeting"""
        result = await self.get("last_greeting_time")
        return float(result) if result else None

    async def set_last_greeting_time(self, timestamp: float):
        """Set timestamp of last greeting"""
        await self.set("last_greeting_time", str(timestamp))


async def should_show_greeting(kv_store: KeyValueStore) -> bool:
    """Check if we should show the greeting message"""
    last_time = await kv_store.get_last_greeting_time()
    if last_time is None:
        return True

    last_datetime = datetime.fromtimestamp(last_time)
    now = datetime.now()

    # Show greeting if last time was on a different day
    return last_datetime.date() < now.date()
