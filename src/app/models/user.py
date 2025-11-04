from uuid6 import uuid7
from datetime import UTC, datetime
import uuid as uuid_pkg

from sqlalchemy import DateTime, ForeignKey, String, Column, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseOAuthAccountTable
from sqlalchemy.orm import DeclarativeBase 
from sqlalchemy.orm import declared_attr
from dataclasses import dataclass, field

from src.app.core.db.database import Base

from uuid6 import uuid7
from datetime import UTC, datetime


class OAuthAccount(SQLAlchemyBaseOAuthAccountTable[int], Base):
    __tablename__ = "oauth_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="cascade"), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts", lazy="joined")


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(30))
    username: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)

    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship("OAuthAccount", back_populates="user")
    profile_image_url: Mapped[str] = mapped_column(String, default="https://profileimageurl.com")

    # Use SQLAlchemy Python-side default= callable rather than dataclass default_factory
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), default=uuid7, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    design_assets: Mapped[list["DesignAsset"]] = relationship(
        "DesignAsset", 
        back_populates="seller"
    )
    cart_items: Mapped[list["CartItem"]] = relationship(
        "CartItem", 
        back_populates="user"
    )
    purchases: Mapped[list["SalesTransaction"]] = relationship(
        "SalesTransaction", 
        back_populates="buyer",
    )
    payouts: Mapped[list["Payout"]] = relationship(
        "Payout", 
        back_populates="seller"
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession", 
        back_populates="user"
    )
    created_labels: Mapped[list["Label"]] = relationship(
        "AssetLabel", 
        back_populates="creator" # Assuming the inverse property in the Label model is named 'creator'
    )
    # no dataclass init flags — use default=None if you want nullable foreign key
    tier_id: Mapped[int | None] = mapped_column(ForeignKey("tier.id"), index=True, nullable=True, default=None)

    is_superuser: Mapped[bool] = mapped_column(default=False)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)

    payment_transactions: Mapped[list["PaymentTransaction"]] = relationship(
        "PaymentTransaction", back_populates="user"
    )
    
    @property
    def full_name(self) -> str:
        return self.name


