"""Schemas for analytics and dashboard functionality."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal


# Dashboard Analytics Schemas
class OverviewStats(BaseModel):
    """Overview statistics for dashboard."""
    total_purchases: int = 0
    total_spent: Decimal = Decimal("0")
    total_sales: int = 0
    total_earned: Decimal = Decimal("0") 
    active_listings: int = 0
    conversion_rate: float = 0.0
    average_order_value: Decimal = Decimal("0")
    customer_satisfaction: float = 0.0


class PerformanceMetrics(BaseModel):
    """Performance metrics for dashboard."""
    views_trend: List[Dict[str, Any]] = Field(default_factory=list)
    sales_trend: List[Dict[str, Any]] = Field(default_factory=list)
    revenue_trend: List[Dict[str, Any]] = Field(default_factory=list)
    top_performing_designs: List[Dict[str, Any]] = Field(default_factory=list)
    category_performance: Dict[str, Any] = Field(default_factory=dict)


class TrafficAnalysis(BaseModel):
    """Traffic analysis for dashboard."""
    direct_search: int = 0
    social_media: int = 0
    referrals: int = 0
    featured: int = 0
    search_keywords: List[str] = Field(default_factory=list)
    geographic_data: Dict[str, Any] = Field(default_factory=dict)


class RecentActivity(BaseModel):
    """Recent activity for dashboard."""
    recent_purchases: List[Dict[str, Any]] = Field(default_factory=list)
    recent_sales: List[Dict[str, Any]] = Field(default_factory=list)
    recent_reviews: List[Dict[str, Any]] = Field(default_factory=list)


class DashboardAnalyticsResponse(BaseModel):
    """Complete dashboard analytics response."""
    user_id: int
    period: str = "30_days"
    overview_stats: OverviewStats
    performance_metrics: PerformanceMetrics
    traffic_analysis: TrafficAnalysis
    recent_activity: RecentActivity
    
    class Config:
        from_attributes = True


# Design Analytics Schemas
class DesignAnalyticsResponse(BaseModel):
    """Analytics data for a specific design."""
    design_id: str
    views: int = 0
    unique_viewers: int = 0
    likes: int = 0
    downloads: int = 0
    revenue: Decimal = Decimal("0")
    conversion_rate: float = 0.0
    average_rating: float = 0.0
    total_reviews: int = 0
    traffic_sources: Dict[str, int] = Field(default_factory=dict)
    performance_trend: List[Dict[str, Any]] = Field(default_factory=list)
    competitor_comparison: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


# User Analytics Schemas
class UserAnalyticsResponse(BaseModel):
    """Analytics data for a user."""
    user_id: int
    date_range: str
    total_views: int = 0
    total_sales: int = 0
    total_revenue: Decimal = Decimal("0")
    new_customers: int = 0
    returning_customers: int = 0
    average_order_value: float = 0.0
    customer_retention_rate: float = 0.0
    top_designs: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


# Performance Analytics Request
class AnalyticsRequest(BaseModel):
    """Request parameters for analytics data."""
    period: str = Field(default="30_days", pattern="^(7_days|30_days|90_days|1_year)$")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    metrics: Optional[List[str]] = Field(default_factory=list)
    
    
# Traffic Analytics Schemas
class TrafficAnalyticsResponse(BaseModel):
    """Traffic analytics response."""
    user_id: int
    period: str
    total_traffic: int = 0
    traffic_sources: Dict[str, int] = Field(default_factory=dict)
    popular_pages: List[Dict[str, Any]] = Field(default_factory=list)
    bounce_rate: float = 0.0
    session_duration: float = 0.0
    
    class Config:
        from_attributes = True


# Earnings Analytics Schemas  
class EarningsAnalyticsResponse(BaseModel):
    """Earnings analytics response."""
    user_id: int
    period: str
    total_earnings: Decimal = Decimal("0")
    earnings_trend: List[Dict[str, Any]] = Field(default_factory=list)
    earnings_by_category: Dict[str, Decimal] = Field(default_factory=dict)
    top_earning_designs: List[Dict[str, Any]] = Field(default_factory=list)
    payout_history: List[Dict[str, Any]] = Field(default_factory=list)
    pending_earnings: Decimal = Decimal("0")
    
    class Config:
        from_attributes = True