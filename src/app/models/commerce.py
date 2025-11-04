"""Commerce system models for design marketplace functionality."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4
import uuid as uuid_pkg

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.app.core.db.database import Base


class DesignAsset(Base):
    """Design assets available in the marketplace."""
    
    __tablename__ = "design_assets"
    
    # Fields without defaults come first
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    seller_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    
    # Fields with defaults come after
    # UUID as Primary Key
    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    category: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # active|draft|sold|paused
    sales: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), default=0)
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    original_model_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("uploaded_models.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    seller = relationship("User", back_populates="design_assets")
    original_model = relationship("UploadedModel", back_populates="design_assets")
    cart_items = relationship("CartItem", back_populates="design_asset")
    sales_transactions = relationship("SalesTransaction", back_populates="design_asset")


class CartItem(Base):
    """Shopping cart items for users."""
    
    __tablename__ = "cart_items"
    
    # Fields without defaults come first
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    
    design_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("design_assets.id"))
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    size: Mapped[str] = mapped_column(String(50))
    color: Mapped[str] = mapped_column(String(50))
    icon: Mapped[str] = mapped_column(String(255))
    
    # Fields with defaults come after
    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    original_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), default=None)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="cart_items")
    design_asset = relationship("DesignAsset", back_populates="cart_items")


class SalesTransaction(Base):
    """Sales transactions for completed purchases."""
    
    __tablename__ = "sales_transactions"
    
    # Fields without defaults come first
    design_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("design_assets.id"))
    
    design_name: Mapped[str] = mapped_column(String(255), nullable=False)
    buyer_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    buyer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    seller_earnings: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    
    # Fields with defaults come after
    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(50), default="completed")  # completed|pending|refunded
    transaction_id: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    commission_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 4), default=0.1)  # 10% default
    
    # Relationships
    design_asset = relationship("DesignAsset", back_populates="sales_transactions")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="purchases")


class Payout(Base):
    """Seller payout requests and processing."""
    
    __tablename__ = "payouts"
    
    # Fields without defaults come first
    seller_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(100))  # paypal|stripe|bank_transfer
    net_amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    
    # Fields with defaults come after
    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending|processing|completed|failed
    request_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    fees: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    payout_account: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    
    # Relationships
    seller = relationship("User", back_populates="payouts")