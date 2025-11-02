from fastapi import APIRouter

from ..api.v1 import router as v1_router

router = APIRouter(prefix="/api")
router.include_router(v1_router)

# Add a simple root endpoint for testing
@router.get("/")
async def root():
    return {"message": "Fluid Simulator Backend API is running!", "status": "healthy"}
