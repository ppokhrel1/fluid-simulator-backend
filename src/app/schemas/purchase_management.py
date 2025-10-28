"""Schemas for purchase management and support functionality."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal


# Purchase Details Schemas
class PurchaseDetailsResponse(BaseModel):
    """Response schema for purchase details."""
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
    
    class Config:
        from_attributes = True


class FileDownloadResponse(BaseModel):
    """Response schema for file download."""
    file_url: str
    filename: str
    file_size: int
    download_expires_at: str
    download_count: int
    max_downloads: int
    
    class Config:
        from_attributes = True


# Support Ticket Schemas  
class SupportTicketRequest(BaseModel):
    """Request schema for creating support tickets."""
    purchase_id: str
    issue_type: str = Field(..., description="Type of issue (download, quality, refund, etc.)")
    subject: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10)
    priority: str = Field(default="medium", regex="^(low|medium|high|urgent)$")
    attachments: Optional[List[str]] = Field(default_factory=list)


class SupportTicketResponse(BaseModel):
    """Response schema for support tickets."""
    ticket_id: str
    status: str
    created_at: str
    estimated_response_time: str
    
    class Config:
        from_attributes = True


class SupportTicketDetails(BaseModel):
    """Detailed support ticket information."""
    id: str
    purchase_id: str
    user_id: int
    issue_type: str
    subject: str
    description: str
    status: str
    priority: str
    assigned_to: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Enhanced Purchase Schema
class PurchaseItem(BaseModel):
    """Individual item in a purchase."""
    design_id: str
    design_name: str
    price: Decimal
    quantity: int = 1
    seller_id: int
    file_urls: List[str] = Field(default_factory=list)


class EnhancedPurchaseResponse(BaseModel):
    """Enhanced purchase response with full details."""
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
    download_links: List[str] = Field(default_factory=list)
    support_eligible: bool = True
    refund_eligible: bool = False
    
    class Config:
        from_attributes = True