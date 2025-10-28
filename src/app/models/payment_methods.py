"""Payment Methods Model for user payout management."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..core.db.database import Base


class PaymentMethod(Base):
    """User payment methods for payouts."""
    
    __tablename__ = "payment_methods"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    method_type = Column(String(50), nullable=False)  # paypal, bank_account, stripe, etc.
    provider = Column(String(100), nullable=False)  # PayPal, Bank of America, etc.
    account_info = Column(Text, nullable=False)  # Encrypted account details
    masked_info = Column(String(255), nullable=True)  # Display-safe info (e.g., "****1234")
    is_primary = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    verification_data = Column(String, default="{}")  # JSON as string for SQLite
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    
    # Relationships
    # user = relationship("User", back_populates="payment_methods")
    
    def __repr__(self):
        return f"<PaymentMethod(id={self.id}, user_id={self.user_id}, type={self.method_type})>"
    
    def set_as_primary(self):
        """Set this payment method as primary."""
        # Note: In a real implementation, you'd want to update other methods for this user
        self.is_primary = True
    
    @property
    def display_name(self) -> str:
        """Get display-friendly name for the payment method."""
        return f"{self.provider} {self.masked_info or '****'}"


class PayoutSettings(Base):
    """User payout configuration settings."""
    
    __tablename__ = "payout_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    auto_payout_enabled = Column(Boolean, default=False)
    payout_threshold = Column(String(10), default="100.00")  # Minimum amount for auto payout
    payout_schedule = Column(String(20), default="monthly")  # weekly, monthly, manual
    primary_payment_method_id = Column(String(36), ForeignKey("payment_methods.id"), nullable=True)
    currency = Column(String(3), default="USD")
    tax_info = Column(String, default="{}")  # JSON as string for SQLite
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # user = relationship("User", back_populates="payout_settings")
    # primary_payment_method = relationship("PaymentMethod")
    
    def __repr__(self):
        return f"<PayoutSettings(user_id={self.user_id}, threshold={self.payout_threshold})>"
    
    @property
    def threshold_amount(self) -> float:
        """Get payout threshold as float."""
        try:
            return float(self.payout_threshold)
        except (ValueError, TypeError):
            return 100.0