# app/models/payment_transactions.py
"""Payment transaction model for storing Stripe payment details."""
from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.app.core.db.database import Base   # <- use the same Base as other models

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stripe_payment_intent_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # single user_id column, consistent FK target
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)

    amount: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="usd")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    refund_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    refund_amount: Mapped[Numeric | None] = mapped_column(Numeric(10, 2), nullable=True)
    refund_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationship back to User
    user: Mapped["User"] = relationship("User", back_populates="payment_transactions", lazy="joined")

    def __repr__(self):
        return f"<PaymentTransaction {self.stripe_payment_intent_id} - {self.status}>"
