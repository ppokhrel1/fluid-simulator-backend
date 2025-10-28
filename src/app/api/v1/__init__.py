# app/api/v1/__init__.py
from fastapi import APIRouter

from .login import router as login_router
from .logout import router as logout_router
from .posts import router as posts_router
from .rate_limits import router as rate_limits_router
from .tasks import router as tasks_router
from .tiers import router as tiers_router
from .users import router as users_router
from .stl_file_handler import router as stl_file_router
from .commerce import router as commerce_router
from .chatbot import router as chatbot_router
from .labels import router as labels_router

# NEW DASHBOARD FUNCTIONALITY ROUTERS
from .purchase_management import router as purchase_management_router
from .analytics import router as analytics_router
from .payment_methods import router as payment_methods_router
from .advanced_tools import router as advanced_tools_router

router = APIRouter(prefix="/v1")
router.include_router(login_router)
router.include_router(logout_router)
router.include_router(users_router)
router.include_router(posts_router)
router.include_router(tasks_router)
router.include_router(tiers_router)
router.include_router(rate_limits_router)
router.include_router(stl_file_router)
router.include_router(commerce_router, prefix="/commerce", tags=["commerce"])
router.include_router(chatbot_router, prefix="/chat", tags=["chatbot"])
router.include_router(labels_router, prefix="/labels", tags=["labels"])

# DASHBOARD FUNCTIONALITY ENDPOINTS
router.include_router(purchase_management_router, prefix="/commerce", tags=["purchase-management"])
router.include_router(analytics_router, tags=["analytics"])
router.include_router(payment_methods_router, tags=["payment-methods"])
router.include_router(advanced_tools_router, tags=["advanced-tools"])
