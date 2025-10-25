from collections.abc import AsyncGenerator
from urllib.parse import quote_plus
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass
import ssl
import os
# Assuming this import path is correct and settings contains your credentials
from ..config import settings 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print("base dir", BASE_DIR)
CA_FILE_PATH = os.path.join(
    BASE_DIR, 
    '..', 
    '..', 
    '..', 
    'certs', 
    'supabase-ca.crt'
)

class Base(DeclarativeBase, MappedAsDataclass):
    pass

# URL-encode the password
encoded_password = quote_plus(settings.POSTGRES_PASSWORD)

# --- REVISED DATABASE_URL CONSTRUCTION ---
DATABASE_URL = (
    f"{settings.POSTGRES_URL}" # <--- sslmode query parameter removed
)

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT) # Use the most common protocol
ssl_context.load_verify_locations(cafile=CA_FILE_PATH)
ssl_context.verify_mode = ssl.CERT_REQUIRED
ssl_context.check_hostname = False # Still disable hostname check for flexibility


# Async engine: Pass the explicit SSL context via connect_args
# This is the most reliable way to enforce SSL connection with asyncpg (especially for Supabase)
async_engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    future=True,
    # This explicit setting is crucial for overriding the way asyncpg
    # handles the 'sslmode' query parameter and properly initiating the SSL handshake.
    connect_args={
        # Forces asyncpg to use the default system trust store for connecting via SSL
        "ssl": ssl_context
    }
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