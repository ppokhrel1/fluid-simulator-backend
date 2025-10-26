from uuid6 import uuid7
from datetime import UTC, datetime
import uuid as uuid_pkg

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    
    name: Mapped[str] = mapped_column(String(30))
    username: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)

    profile_image_url: Mapped[str] = mapped_column(String, default="https://profileimageurl.com")
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), default=uuid7, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    tier_id: Mapped[int | None] = mapped_column(ForeignKey("tier.id"), index=True, default=None)
    
    # Commerce relationships
    design_assets = relationship("DesignAsset", back_populates="seller")
    cart_items = relationship("CartItem", back_populates="user")
    purchases = relationship("SalesTransaction", foreign_keys="SalesTransaction.buyer_id", back_populates="buyer")
    payouts = relationship("Payout", back_populates="seller")
    
    # Chatbot relationships
    chat_sessions = relationship("ChatSession", back_populates="user")
    
    # Labeling relationships
    created_labels = relationship("AssetLabel", back_populates="creator")
    
    @property
    def full_name(self) -> str:
        """Frontend-compatible full_name property."""
        return self.name