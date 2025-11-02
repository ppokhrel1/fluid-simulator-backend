"""Purchase Details Model for Dashboard functionality."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid as uuid_pkg
import uuid

from ..core.db.database import Base


class PurchaseDetails(Base):
    """Extended purchase details for file downloads and support."""
    
    __tablename__ = "purchase_details"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("sales_transactions.id"), 
        nullable=False
    )
    item_details = Column(JSON, nullable=False, default=dict)
    download_links = Column(JSON, default=list)
    download_count = Column(Integer, default=0)
    max_downloads = Column(Integer, default=5)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    # purchase = relationship("Purchase", back_populates="details")
    
    def __repr__(self):
        return f"<PurchaseDetails(id={self.id}, purchase_id={self.purchase_id})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if download links have expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def downloads_remaining(self) -> int:
        """Calculate remaining downloads."""
        return max(0, self.max_downloads - self.download_count)
    
    def can_download(self) -> bool:
        """Check if file can still be downloaded."""
        return not self.is_expired and self.downloads_remaining > 0