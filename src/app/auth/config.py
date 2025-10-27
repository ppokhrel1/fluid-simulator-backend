# app/auth/config.py
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from ..models.user import User, OAuthAccount
from .manager import get_user_manager

# Bearer token transport
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

# JWT strategy
def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret="your-secret-key",  # Use environment variable in production
        lifetime_seconds=3600
    )

# Authentication backend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# FastAPI Users instance
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

# Get current user (compatible with your existing system)
current_active_user = fastapi_users.current_user(active=True)