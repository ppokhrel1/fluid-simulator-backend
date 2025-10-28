"""Schemas for advanced tools functionality."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal


# Pricing Analysis Schemas
class PricingAnalysisRequest(BaseModel):
    """Request schema for pricing analysis."""
    design_ids: List[str] = Field(..., min_items=1)
    include_competitors: bool = True
    market_analysis_depth: str = Field(default="standard", regex="^(basic|standard|detailed)$")


class MarketAnalysis(BaseModel):
    """Market analysis data."""
    competitor_prices: List[Dict[str, Any]] = Field(default_factory=list)
    price_trend: str = "stable"  # rising, falling, stable, volatile
    demand_level: str = "medium"  # low, medium, high
    market_saturation: float = 0.0
    recommended_price_range: Dict[str, Decimal] = Field(default_factory=dict)


class PricingAnalysisResponse(BaseModel):
    """Response schema for pricing analysis."""
    design_id: str
    current_price: Decimal
    suggested_price: Decimal
    price_confidence: float = 0.0  # 0-1 confidence score
    market_analysis: MarketAnalysis
    optimization_suggestions: List[str] = Field(default_factory=list)
    potential_revenue_impact: Dict[str, Decimal] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


# Review Management Schemas
class ReviewSummary(BaseModel):
    """Summary of reviews for a user."""
    average_rating: float = 0.0
    total_reviews: int = 0
    rating_distribution: Dict[str, int] = Field(default_factory=dict)  # "5": 10, "4": 5, etc.
    response_needed: int = 0
    sentiment_analysis: Dict[str, float] = Field(default_factory=dict)


class ReviewDetails(BaseModel):
    """Individual review details."""
    id: str
    design_id: str
    design_name: str
    reviewer_name: str
    rating: int
    comment: str
    created_at: datetime
    response: Optional[str] = None
    response_date: Optional[datetime] = None
    needs_response: bool = False
    sentiment: str = "neutral"  # positive, negative, neutral
    
    class Config:
        from_attributes = True


class ReviewManagementResponse(BaseModel):
    """Response schema for review management."""
    reviews: List[ReviewDetails]
    summary: ReviewSummary
    actionable_insights: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class ReviewResponseRequest(BaseModel):
    """Request schema for responding to reviews."""
    response: str = Field(..., min_length=10, max_length=1000)
    is_public: bool = True
    acknowledge_feedback: bool = True


class ReviewResponseResponse(BaseModel):
    """Response schema for review responses."""
    review_id: str
    response: str
    response_date: datetime
    status: str = "published"
    message: str = "Response published successfully"
    
    class Config:
        from_attributes = True


# Promotion Campaign Schemas
class PromotionCampaignRequest(BaseModel):
    """Request schema for creating promotion campaigns."""
    campaign_name: str = Field(..., min_length=3, max_length=255)
    design_ids: List[str] = Field(..., min_items=1)
    campaign_type: str = Field(..., regex="^(featured|boost|sponsored|premium|flash_sale)$")
    duration: int = Field(..., ge=1, le=90)  # days
    budget: Decimal = Field(..., gt=0)
    target_audience: Dict[str, Any] = Field(default_factory=dict)
    promotion_settings: Dict[str, Any] = Field(default_factory=dict)


class PromotionCampaignResponse(BaseModel):
    """Response schema for promotion campaigns."""
    campaign_id: str
    campaign_name: str
    design_ids: List[str]
    campaign_type: str
    duration: int
    budget: Decimal
    status: str
    estimated_reach: int = 0
    estimated_clicks: int = 0
    estimated_conversions: int = 0
    created_at: datetime
    expires_at: datetime
    
    class Config:
        from_attributes = True


# Customer Analytics Schemas
class CustomerSegment(BaseModel):
    """Customer segment data."""
    segment_name: str
    customer_count: int
    total_revenue: Decimal
    average_order_value: Decimal
    repeat_purchase_rate: float
    characteristics: List[str] = Field(default_factory=list)


class CustomerBehavior(BaseModel):
    """Customer behavior analysis."""
    purchase_patterns: Dict[str, Any] = Field(default_factory=dict)
    preferred_categories: List[str] = Field(default_factory=list)
    seasonal_trends: Dict[str, Any] = Field(default_factory=dict)
    price_sensitivity: str = "medium"  # low, medium, high
    loyalty_score: float = 0.0


class CustomerAnalyticsResponse(BaseModel):
    """Response schema for customer analytics."""
    user_id: int
    total_customers: int
    new_customers_this_month: int
    returning_customers: int
    customer_segments: List[CustomerSegment] = Field(default_factory=list)
    customer_behavior: CustomerBehavior
    churn_risk: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


# Competitive Analysis Schema
class CompetitorData(BaseModel):
    """Competitor analysis data."""
    competitor_name: str
    similar_designs_count: int
    average_price: Decimal
    market_share_estimate: float
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)


class CompetitiveAnalysisResponse(BaseModel):
    """Response schema for competitive analysis."""
    user_id: int
    category: str
    competitors: List[CompetitorData] = Field(default_factory=list)
    market_position: str = "unknown"  # leader, challenger, follower, niche
    competitive_advantages: List[str] = Field(default_factory=list)
    improvement_opportunities: List[str] = Field(default_factory=list)
    market_trends: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True