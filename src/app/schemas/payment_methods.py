"""Schemas for payment methods and payout settings."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from decimal import Decimal


# Payment Method Schemas
class PaymentMethodCreate(BaseModel):
    """Schema for creating payment methods."""
    method_type: str = Field(..., pattern="^(paypal|bank_account|stripe|venmo|cashapp)$")
    provider: str = Field(..., min_length=1, max_length=100)
    account_info: str = Field(..., min_length=1)  # Will be encrypted
    is_primary: bool = False


class PaymentMethodUpdate(BaseModel):
    """Schema for updating payment methods."""
    provider: Optional[str] = Field(None, min_length=1, max_length=100)
    account_info: Optional[str] = None  # Will be encrypted
    is_primary: Optional[bool] = None


class PaymentMethodResponse(BaseModel):
    """Schema for payment method responses."""
    id: str
    user_id: int
    method_type: str
    provider: str
    masked_info: Optional[str] = None  # Display-safe info
    is_primary: bool
    is_verified: bool
    created_at: datetime
    last_used: Optional[datetime] = None
    display_name: str = ""
    
    @validator('display_name', always=True)
    def set_display_name(cls, v, values):
        if not v and 'provider' in values and 'masked_info' in values:
            masked = values.get('masked_info', '****')
            return f"{values['provider']} {masked}"
        return v
    
    class Config:
        from_attributes = True


# Payout Settings Schemas
class PayoutSettingsUpdate(BaseModel):
    """Schema for updating payout settings."""
    auto_payout_enabled: Optional[bool] = None
    payout_threshold: Optional[Decimal] = Field(None, ge=Decimal("10.00"), le=Decimal("10000.00"))
    payout_schedule: Optional[str] = Field(None, pattern="^(weekly|monthly|manual)$")
    primary_payment_method_id: Optional[str] = None
    currency: Optional[str] = Field(None, pattern="^(USD|EUR|GBP|CAD|AUD)$")
    tax_info: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PayoutSettingsResponse(BaseModel):
    """Schema for payout settings responses."""
    user_id: int
    auto_payout_enabled: bool
    payout_threshold: Decimal
    payout_schedule: str
    primary_payment_method_id: Optional[str] = None
    currency: str
    tax_info: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    threshold_amount: float = 0.0
    
    @validator('threshold_amount', always=True)
    def set_threshold_amount(cls, v, values):
        if 'payout_threshold' in values:
            return float(values['payout_threshold'])
        return v
    
    class Config:
        from_attributes = True


# Payout History Schema
class PayoutRecord(BaseModel):
    """Schema for payout records."""
    id: str
    user_id: int
    amount: Decimal
    currency: str
    payment_method_id: str
    status: str  # pending, processing, completed, failed
    transaction_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class PayoutHistoryResponse(BaseModel):
    """Schema for payout history responses."""
    total_payouts: int
    total_amount: Decimal
    payouts: List[PayoutRecord]
    pending_amount: Decimal = Decimal("0")
    next_payout_date: Optional[str] = None
    
    class Config:
        from_attributes = True


# Earnings Summary Schema
class EarningsSummary(BaseModel):
    """Schema for earnings summary."""
    total_earnings: Decimal = Decimal("0")
    available_for_payout: Decimal = Decimal("0")
    pending_payout: Decimal = Decimal("0")
    total_paid_out: Decimal = Decimal("0")
    current_month_earnings: Decimal = Decimal("0")
    last_payout_date: Optional[datetime] = None
    next_payout_date: Optional[str] = None
    
    class Config:
        from_attributes = True


# Payment Method Verification Schema
class PaymentMethodVerificationRequest(BaseModel):
    """Schema for payment method verification."""
    verification_code: Optional[str] = None
    verification_document: Optional[str] = None  # Base64 encoded or file path
    additional_info: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PaymentMethodVerificationResponse(BaseModel):
    """Schema for payment method verification response."""
    payment_method_id: str
    verification_status: str  # pending, verified, failed, requires_action
    verification_message: str
    required_actions: List[str] = Field(default_factory=list)
    estimated_verification_time: Optional[str] = None
    
    class Config:
        from_attributes = True