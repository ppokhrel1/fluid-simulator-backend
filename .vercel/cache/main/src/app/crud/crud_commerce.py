"""CRUD operations for commerce system."""

from typing import Any, Dict, List, Optional
from fastcrud import FastCRUD
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..models.commerce import DesignAsset, CartItem, SalesTransaction, Payout
from ..schemas.commerce import (
    DesignAssetCreate, DesignAssetUpdate, DesignAssetUpdateInternal, DesignAssetDelete, DesignAssetRead,
    CartItemCreate, CartItemUpdate, CartItemUpdateInternal, CartItemDelete, CartItemRead,
    SalesTransactionCreate, SalesTransactionUpdate, SalesTransactionUpdateInternal, SalesTransactionDelete, SalesTransactionRead,
    PayoutCreate, PayoutUpdate, PayoutUpdateInternal, PayoutDelete, PayoutRead
)


CRUDDesignAsset = FastCRUD[DesignAsset, DesignAssetCreate, DesignAssetUpdate, DesignAssetUpdateInternal, DesignAssetDelete, DesignAssetRead]

class DesignAssetCRUD(CRUDDesignAsset):
    async def get_by_category(
        self, 
        db: AsyncSession, 
        category: str, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[DesignAsset]:
        """Get design assets by category."""
        stmt = select(self.model).where(
            self.model.category == category,
            self.model.status == "active"
        ).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def increment_views(self, db: AsyncSession, design_id: str) -> None:
        """Increment view count for a design."""
        stmt = select(self.model).where(self.model.id == design_id)
        result = await db.execute(stmt)
        design = result.scalar_one_or_none()
        if design:
            design.views += 1
            await db.commit()
    
    async def increment_likes(self, db: AsyncSession, design_id: str) -> None:
        """Increment like count for a design."""
        stmt = select(self.model).where(self.model.id == design_id)
        result = await db.execute(stmt)
        design = result.scalar_one_or_none()
        if design:
            design.likes += 1
            await db.commit()


CRUDCartItem = FastCRUD[CartItem, CartItemCreate, CartItemUpdate, CartItemUpdateInternal, CartItemDelete, CartItemRead]

class CartItemCRUD(CRUDCartItem):
    async def get_user_cart(self, db: AsyncSession, user_id: int) -> List[CartItem]:
        """Get all cart items for a user."""
        stmt = select(self.model).where(self.model.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def clear_user_cart(self, db: AsyncSession, user_id: int) -> None:
        """Clear all items from user's cart."""
        stmt = select(self.model).where(self.model.user_id == user_id)
        result = await db.execute(stmt)
        items = result.scalars().all()
        for item in items:
            await db.delete(item)
        await db.commit()


CRUDSalesTransaction = FastCRUD[SalesTransaction, SalesTransactionCreate, SalesTransactionUpdate, SalesTransactionUpdateInternal, SalesTransactionDelete, SalesTransactionRead]

class SalesTransactionCRUD(CRUDSalesTransaction):
    async def get_user_purchases(self, db: AsyncSession, user_id: int) -> List[SalesTransaction]:
        """Get all purchases for a user."""
        stmt = select(self.model).where(self.model.buyer_id == user_id)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_seller_sales(self, db: AsyncSession, seller_id: int) -> List[SalesTransaction]:
        """Get all sales for a seller."""
        stmt = (
            select(self.model)
            .join(DesignAsset, self.model.design_id == DesignAsset.id)
            .where(DesignAsset.seller_id == seller_id)
        )
        result = await db.execute(stmt)
        return result.scalars().all()


CRUDPayout = FastCRUD[Payout, PayoutCreate, PayoutUpdate, PayoutUpdateInternal, PayoutDelete, PayoutRead]

class PayoutCRUD(CRUDPayout):
    async def get_seller_payouts(self, db: AsyncSession, seller_id: int) -> List[Payout]:
        """Get all payouts for a seller."""
        stmt = select(self.model).where(self.model.seller_id == seller_id)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_pending_payouts(self, db: AsyncSession) -> List[Payout]:
        """Get all pending payouts."""
        stmt = select(self.model).where(self.model.status == "pending")
        result = await db.execute(stmt)
        return result.scalars().all()


# Create instances
design_asset_crud = DesignAssetCRUD(DesignAsset)
cart_item_crud = CartItemCRUD(CartItem)
sales_transaction_crud = SalesTransactionCRUD(SalesTransaction)
payout_crud = PayoutCRUD(Payout)