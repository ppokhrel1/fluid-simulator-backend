"""Schemas for payment management with Stripe integration."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal


# Payment Intent Schemas
class PaymentIntentRequest(BaseModel):
    """Request schema for creating payment intent."""
    amount: Decimal = Field(..., gt=0, description="Amount in dollars")
    currency: str = Field(default="usd", pattern="^(usd|eur|gbp|cad|aud)$")
    items: List[Dict[str, Any]] = Field(..., description="List of items being purchased")
    purchase_type: str = Field(default="one_time", pattern="^(one_time|subscription)$")
    payment_method_types: Optional[List[str]] = Field(
        default=None, 
        description="Stripe payment method types"
    )
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PaymentIntentResponse(BaseModel):
    """Response schema for payment intent."""
    payment_intent_id: str
    client_secret: str
    amount: Decimal
    currency: str
    status: str
    created: int
    payment_method_types: List[str]
    next_action: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class PaymentConfirmationRequest(BaseModel):
    """Request schema for confirming payment."""
    payment_intent_id: str
    payment_method_id: str
    items: List[Dict[str, Any]]
    return_url: Optional[str] = None


class PaymentConfirmationResponse(BaseModel):
    """Response schema for payment confirmation."""
    payment_intent_id: str
    status: str
    sales_transaction_id: Optional[str] = None
    amount: Decimal
    currency: str
    receipt_url: Optional[str] = None
    confirmed_at: str
    
    class Config:
        from_attributes = True


# Refund Schemas
class RefundRequest(BaseModel):
    """Request schema for refund."""
    payment_intent_id: str
    amount: Optional[Decimal] = Field(None, gt=0)
    reason: Optional[str] = Field(
        None, 
        pattern="^(requested_by_customer|duplicate|fraudulent)$"
    )


class RefundResponse(BaseModel):
    """Response schema for refund."""
    refund_id: str
    payment_intent_id: str
    amount: Decimal
    currency: str
    status: str
    reason: Optional[str] = None
    created: int
    
    class Config:
        from_attributes = True


# Payment Method Schemas
class CardDetails(BaseModel):
    """Schema for card details."""
    brand: str
    last4: str
    exp_month: int
    exp_year: int


class PaymentMethodResponse(BaseModel):
    """Response schema for payment methods."""
    id: str
    type: str
    card: Optional[CardDetails] = None
    created: int
    
    class Config:
        from_attributes = True


# Subscription Plan Schemas
class SubscriptionPlanResponse(BaseModel):
    """Response schema for subscription plans."""
    plan_id: str
    product_id: str
    name: str
    description: Optional[str] = None
    amount: Decimal
    currency: str
    interval: str
    interval_count: int
    features: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


# Webhook Schemas
class StripeWebhookResponse(BaseModel):
    """Response schema for Stripe webhook."""
    status: str
    processed_events: List[str] = Field(default_factory=list)




class PurchaseDetailsResponse(BaseModel):
    id: str
    purchase_date: str
    items: List[Dict[str, Any]]
    total: Decimal
    subtotal: Decimal
    tax: Decimal
    status: str
    buyer_info: Dict[str, Any]
    seller_info: Dict[str, Any]
    transaction_id: str
    payment_method: str
    shipping_info: Optional[Dict[str, Any]] = None


class FileDownloadResponse(BaseModel):
    """Response schema for file download."""
    file_url: str
    filename: str
    file_size: int
    download_expires_at: str
    download_count: int
    max_downloads: int


class SupportTicketRequest(BaseModel):
    """Request schema for creating a support ticket."""
    issue_type: str = Field(..., pattern="^(technical|billing|refund|other)$")
    subject: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=1000)
    priority: str = Field(default="medium", pattern="^(urgent|high|medium|low)$")
    attachments: Optional[List[str]] = Field(default_factory=list)


class SupportTicketResponse(BaseModel):
    """Response schema for support ticket."""
    ticket_id: str
    status: str
    created_at: str
    estimated_response_time: str




class PurchaseItem(BaseModel):
    """Schema for a purchased item."""
    design_id: str
    design_name: str
    price: Decimal
    quantity: int
    seller_id: int
    file_urls: List[str] = Field(default_factory=list)



class EnhancedPurchaseResponse(BaseModel):
    """Enhanced purchase response schema."""
    id: str
    items: List[PurchaseItem]
    total: Decimal
    subtotal: Decimal
    tax: Decimal
    purchaseDate: datetime
    userId: str
    status: str
    payment_method: str
    transaction_id: str
    download_links: List[Dict[str, Any]] = Field(default_factory=list)
    support_eligible: bool
    refund_eligible: bool