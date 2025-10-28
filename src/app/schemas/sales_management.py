"""Schemas for sales management and design editing functionality."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal


# Design Update Schemas
class DesignUpdateRequest(BaseModel):
    """Request schema for updating design listings."""
    designName: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    price: Optional[Decimal] = Field(None, gt=0)
    category: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    technicalSpecs: Optional[str] = None
    instructions: Optional[str] = None
    status: Optional[str] = Field(None, regex="^(active|draft|paused|sold)$")


class DesignUpdateResponse(BaseModel):
    """Response schema for design updates."""
    id: str
    designName: str
    description: str
    price: Decimal
    category: str
    status: str
    lastModified: datetime
    message: str = "Design updated successfully"
    
    class Config:
        from_attributes = True


# Promotion Schemas
class PromotionRequest(BaseModel):
    """Request schema for promoting designs."""
    promotion_type: str = Field(..., regex="^(featured|boost|sponsored|premium)$")
    duration_days: int = Field(..., ge=1, le=90)
    budget: Optional[Decimal] = Field(None, gt=0)
    target_categories: Optional[List[str]] = Field(default_factory=list)
    boost_percentage: Optional[int] = Field(None, ge=10, le=500)


class PromotionResponse(BaseModel):
    """Response schema for promotion campaigns."""
    campaign_id: str
    design_id: str
    campaign_type: str
    status: str
    duration_days: int
    budget: Optional[Decimal] = None
    created_at: datetime
    expires_at: datetime
    estimated_reach: int = 0
    message: str = "Promotion campaign created successfully"
    
    class Config:
        from_attributes = True


# Design Duplication Schema
class DesignDuplicateRequest(BaseModel):
    """Request schema for duplicating designs."""
    new_name: str = Field(..., min_length=1, max_length=255)
    copy_price: bool = True
    copy_description: bool = True
    copy_tags: bool = True
    status: str = Field(default="draft", regex="^(active|draft)$")


class DesignDuplicateResponse(BaseModel):
    """Response schema for design duplication."""
    original_id: str
    new_id: str
    new_name: str
    status: str
    created_at: datetime
    message: str = "Design duplicated successfully"
    
    class Config:
        from_attributes = True


# Status Update Schema
class DesignStatusUpdateRequest(BaseModel):
    """Request schema for updating design status."""
    status: str = Field(..., regex="^(active|draft|paused|sold|featured|promoted)$")
    reason: Optional[str] = None


class DesignStatusUpdateResponse(BaseModel):
    """Response schema for status updates."""
    id: str
    old_status: str
    new_status: str
    updated_at: datetime
    message: str = "Design status updated successfully"
    
    class Config:
        from_attributes = True


# Enhanced Design Schema
class EnhancedDesignResponse(BaseModel):
    """Enhanced design response with sales data."""
    id: str
    name: str
    description: str
    price: Decimal
    category: str
    status: str
    sales: int = 0
    revenue: Decimal = Decimal("0")
    uploadDate: datetime
    lastModified: datetime
    views: int = 0
    likes: int = 0
    downloads: int = 0
    rating: float = 0.0
    review_count: int = 0
    seller_id: int
    original_model_id: Optional[int] = None
    promotion_status: Optional[str] = None
    promotion_expires: Optional[datetime] = None
    featured: bool = False
    trending: bool = False
    
    class Config:
        from_attributes = True


# Bulk Operations Schema
class BulkDesignUpdateRequest(BaseModel):
    """Request schema for bulk design updates."""
    design_ids: List[str] = Field(..., min_items=1)
    updates: DesignUpdateRequest
    
    
class BulkOperationResponse(BaseModel):
    """Response schema for bulk operations."""
    total_requested: int
    successful_updates: int
    failed_updates: int
    updated_designs: List[str]
    errors: List[Dict[str, str]] = Field(default_factory=list)
    message: str
    
    class Config:
        from_attributes = True