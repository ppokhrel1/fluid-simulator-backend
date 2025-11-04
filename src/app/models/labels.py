"""3D model labeling system models."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.app.core.db.database import Base


class AssetLabel(Base):
    """3D position-based labels for uploaded models."""
    
    __tablename__ = "asset_labels"
    
    # Fields without defaults come first
    model_id: Mapped[int] = mapped_column(Integer, ForeignKey("uploaded_models.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    
    # Fields with defaults come after
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    position_x: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 6), default=None)
    position_y: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 6), default=None)
    position_z: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 6), default=None)
    category: Mapped[Optional[str]] = mapped_column(String(100), default=None)  # Material|Part|Function|Texture|Dimension|Other
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    model = relationship("UploadedModel", back_populates="labels")
    creator = relationship("User", back_populates="created_labels")