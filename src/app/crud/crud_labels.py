"""CRUD operations for labeling system."""

from typing import List, Optional
from fastcrud import FastCRUD
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.app.models.labels import AssetLabel
from src.app.schemas.labels import LabelCreate, LabelUpdate, LabelUpdateInternal, LabelDelete, LabelRead


CRUDLabel = FastCRUD[AssetLabel, LabelCreate, LabelUpdate, LabelUpdateInternal, LabelDelete, LabelRead]

class LabelCRUD(CRUDLabel):
    async def get_model_labels(self, db: AsyncSession, model_id: str) -> List[AssetLabel]:
        """Get all labels for a specific model."""
        stmt = select(self.model).where(self.model.model_id == model_id)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_user_labels(self, db: AsyncSession, user_id: int) -> List[AssetLabel]:
        """Get all labels created by a user."""
        stmt = select(self.model).where(self.model.created_by == user_id)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_labels_by_category(self, db: AsyncSession, category: str) -> List[AssetLabel]:
        """Get labels by category."""
        stmt = select(self.model).where(self.model.category == category)
        result = await db.execute(stmt)
        return result.scalars().all()


# Create instance
label_crud = LabelCRUD(AssetLabel)