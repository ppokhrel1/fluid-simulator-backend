from fastcrud import FastCRUD

from src.app.models.tier import Tier
from src.app.schemas.tier import TierCreateInternal, TierDelete, TierRead, TierUpdate, TierUpdateInternal

CRUDTier = FastCRUD[Tier, TierCreateInternal, TierUpdate, TierUpdateInternal, TierDelete, TierRead]
crud_tiers = CRUDTier(Tier)
