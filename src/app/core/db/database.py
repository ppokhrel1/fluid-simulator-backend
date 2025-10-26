from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from ..config import settings 

class Base(DeclarativeBase):
    pass

# Use SQLite for development - simpler setup
DATABASE_URL = f"{settings.SQLITE_ASYNC_PREFIX}{settings.SQLITE_URI}"

# Async engine for SQLite
async_engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    future=True,
    connect_args={"check_same_thread": False}  # SQLite specific setting
)

# Session maker
local_session = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def async_get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to yield an asynchronous database session.
    The session is automatically closed upon exiting the context.
    """
    async with local_session() as db:
        yield db