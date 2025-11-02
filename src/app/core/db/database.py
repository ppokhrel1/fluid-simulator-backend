from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from ..config import settings 

class Base(DeclarativeBase):
    pass

# Database selection - use Supabase if configured, otherwise SQLite
if hasattr(settings, 'POSTGRES_URL') and settings.POSTGRES_URL and "supabase" in settings.POSTGRES_URL:
    # Use Supabase PostgreSQL for production
    DATABASE_URL = settings.POSTGRES_URL
    print(f"🌐 Attempting Supabase connection: {DATABASE_URL[:50]}...")
    
    # Async engine for PostgreSQL/Supabase
    async_engine = create_async_engine(
        DATABASE_URL, 
        echo=False, 
        future=True,
        pool_pre_ping=True,  # PostgreSQL specific - validates connections
        pool_recycle=300,    # Recycle connections every 5 minutes
        connect_args={
            "server_settings": {
                "application_name": "fluid-simulator-backend",
            }
        }
    )
    print("✅ Supabase engine created (connection will be tested on first use)")
    print("⚠️  If connection fails, server will automatically fall back to SQLite")
else:
    # Fallback to SQLite for development  
    DATABASE_URL = f"{settings.SQLITE_ASYNC_PREFIX}{settings.SQLITE_URI}"
    print(f"📁 Using SQLite database: {DATABASE_URL}")
    
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