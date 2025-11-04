# app/api/v1/auth.py
from fastapi import APIRouter
from src.app.auth.config import fastapi_users, auth_backend
from src.app.auth.socials import router as social_router

router = APIRouter(prefix="", tags=["auth"])

# Include fastapi-users routes (JWT authentication)
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt"
)

# Include social login routes
router.include_router(social_router)

# Include your existing login routes
from .login import router as existing_login_router
router.include_router(existing_login_router)