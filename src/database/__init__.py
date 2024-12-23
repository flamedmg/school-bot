from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings

from .models import Base

# Convert SQLite URL to async version
db_url = settings.database_url.replace("sqlite:", "sqlite+aiosqlite:")

# Create async engine
engine = create_async_engine(
    db_url,
    echo=True,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """Initialize database"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return True


async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        yield session
