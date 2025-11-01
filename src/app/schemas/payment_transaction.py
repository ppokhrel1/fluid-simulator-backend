"""Schemas for payment transactions."""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal


class PaymentTransactionBase(BaseModel):
    """Base schema for payment transactions."""
    stripe_payment_intent_id: str
    stripe_customer_id: Optional[str] = None
    user_id: int
    amount: Decimal
    currency: str = "usd"
    status: str = "pending"
    payment_method: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentTransactionCreate(PaymentTransactionBase):
    """Schema for creating payment transactions."""
    pass


class PaymentTransactionUpdate(BaseModel):
    """Schema for updating payment transactions."""
    status: Optional[str] = None
    payment_method: Optional[str] = None
    refund_id: Optional[str] = None
    refund_amount: Optional[Decimal] = None
    refund_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentTransactionResponse(PaymentTransactionBase):
    """Response schema for payment transactions."""
    id: str
    refund_id: Optional[str] = None
    refund_amount: Optional[Decimal] = None
    refund_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentTransactionRefund(BaseModel):
    """Schema for refunding payment transactions."""
    refund_amount: Optional[Decimal] = None
    refund_reason: Optional[str] = None