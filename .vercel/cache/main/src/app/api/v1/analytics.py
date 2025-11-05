"""Analytics endpoints for Dashboard functionality."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from ...core.db.database import async_get_db
from ...core.security import get_current_user
from ...models.user import User
from ...schemas.analytics import (
    DashboardAnalyticsResponse,
    OverviewStats,
    PerformanceMetrics,
    TrafficAnalysis,
    RecentActivity,
    UserAnalyticsResponse,
    TrafficAnalyticsResponse,
    EarningsAnalyticsResponse,
    AnalyticsRequest
)
from ...crud import (
    crud_user_analytics, 
    crud_design_analytics,
    sales_transaction_crud
)
from ...crud.crud_commerce import design_asset_crud
from decimal import Decimal

router = APIRouter(prefix="/analytics", tags=["Dashboard Analytics"])


@router.get("/dashboard/{user_id}", response_model=DashboardAnalyticsResponse)
async def get_dashboard_analytics(
    user_id: int,
    period: str = Query(default="30_days", regex="^(7_days|30_days|90_days|1_year)$"),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive dashboard analytics for a user."""
    
    # Verify access
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Calculate date range
    days_map = {"7_days": 7, "30_days": 30, "90_days": 90, "1_year": 365}
    days = days_map.get(period, 30)
    
    # Get user analytics
    user_stats = await crud_user_analytics.get_aggregated_user_stats(db, user_id, days)
    
    # Get user's designs for additional metrics
    user_designs = await design_asset_crud.get_seller_designs(db, user_id)
    active_listings = len([d for d in user_designs if d.status == "active"])
    
    # Get recent purchases (mock data for now)
    recent_purchases = await sales_transaction_crud.get_user_transactions(db, user_id, 5)
    
    # Build overview stats
    overview_stats = OverviewStats(
        total_purchases=len(recent_purchases),
        total_spent=sum(p.total for p in recent_purchases),
        total_sales=user_stats.get('total_sales', 0),
        total_earned=user_stats.get('total_revenue', Decimal('0')),
        active_listings=active_listings,
        conversion_rate=user_stats.get('customer_retention_rate', 0.0),
        average_order_value=Decimal(str(user_stats.get('average_order_value', 0.0))),
        customer_satisfaction=4.7  # Mock value
    )
    
    # Build performance metrics
    performance_metrics = PerformanceMetrics(
        views_trend=[
            {"date": "2025-10-25", "views": 120},
            {"date": "2025-10-26", "views": 150},
            {"date": "2025-10-27", "views": 180},
            {"date": "2025-10-28", "views": 145}
        ],
        sales_trend=[
            {"date": "2025-10-25", "sales": 2},
            {"date": "2025-10-26", "sales": 3},
            {"date": "2025-10-27", "sales": 5},
            {"date": "2025-10-28", "sales": 4}
        ],
        revenue_trend=[
            {"date": "2025-10-25", "revenue": 45.00},
            {"date": "2025-10-26", "revenue": 67.50},
            {"date": "2025-10-27", "revenue": 112.25},
            {"date": "2025-10-28", "revenue": 89.75}
        ],
        top_performing_designs=[
            {"design_id": "design1", "name": "Aerospace Wing", "sales": 12, "revenue": 240.00},
            {"design_id": "design2", "name": "Turbine Blade", "sales": 8, "revenue": 160.00},
            {"design_id": "design3", "name": "Heat Exchanger", "sales": 6, "revenue": 120.00}
        ],
        category_performance={
            "aerospace": {"sales": 15, "revenue": 300.00},
            "automotive": {"sales": 8, "revenue": 160.00},
            "industrial": {"sales": 12, "revenue": 240.00}
        }
    )
    
    # Build traffic analysis
    traffic_analysis = TrafficAnalysis(
        direct_search=450,
        social_media=180,
        referrals=120,
        featured=90,
        search_keywords=["aerospace", "turbine", "CAD", "3D printing", "engineering"],
        geographic_data={
            "US": 35,
            "EU": 25,
            "Asia": 20,
            "Others": 20
        }
    )
    
    # Build recent activity
    recent_activity = RecentActivity(
        recent_purchases=[
            {
                "id": p.id,
                "design_name": "Mock Design",
                "amount": float(p.total),
                "date": p.purchaseDate.isoformat()
            } for p in recent_purchases[:3]
        ],
        recent_sales=[
            {"design_name": "Aerospace Wing", "amount": 25.00, "buyer": "user123", "date": "2025-10-28"},
            {"design_name": "Turbine Blade", "amount": 20.00, "buyer": "user456", "date": "2025-10-27"},
            {"design_name": "Heat Exchanger", "amount": 30.00, "buyer": "user789", "date": "2025-10-26"}
        ],
        recent_reviews=[
            {"design_name": "Aerospace Wing", "rating": 5, "comment": "Excellent quality!", "date": "2025-10-28"},
            {"design_name": "Turbine Blade", "rating": 4, "comment": "Good design, fast delivery", "date": "2025-10-27"}
        ]
    )
    
    return DashboardAnalyticsResponse(
        user_id=user_id,
        period=period,
        overview_stats=overview_stats,
        performance_metrics=performance_metrics,
        traffic_analysis=traffic_analysis,
        recent_activity=recent_activity
    )


@router.get("/performance/{user_id}", response_model=UserAnalyticsResponse)
async def get_performance_analytics(
    user_id: int,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed performance analytics for a user."""
    
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get user analytics
    stats = await crud_user_analytics.get_aggregated_user_stats(db, user_id, days)
    
    return UserAnalyticsResponse(
        user_id=user_id,
        date_range=f"{days}_days",
        total_views=stats.get('total_views', 0),
        total_sales=stats.get('total_sales', 0),
        total_revenue=stats.get('total_revenue', Decimal('0')),
        new_customers=stats.get('new_customers', 0),
        returning_customers=stats.get('returning_customers', 0),
        average_order_value=stats.get('average_order_value', 0.0),
        customer_retention_rate=stats.get('customer_retention_rate', 0.0),
        top_designs=[
            {"design_id": "design1", "name": "Aerospace Wing", "performance_score": 95},
            {"design_id": "design2", "name": "Turbine Blade", "performance_score": 87},
            {"design_id": "design3", "name": "Heat Exchanger", "performance_score": 82}
        ]
    )


@router.get("/traffic/{user_id}", response_model=TrafficAnalyticsResponse)
async def get_traffic_analytics(
    user_id: int,
    period: str = Query(default="30_days", regex="^(7_days|30_days|90_days|1_year)$"),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get traffic analytics for a user."""
    
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return TrafficAnalyticsResponse(
        user_id=user_id,
        period=period,
        total_traffic=1250,
        traffic_sources={
            "direct_search": 450,
            "social_media": 280,
            "referrals": 320,
            "featured": 200
        },
        popular_pages=[
            {"page": "/designs/aerospace-wing", "views": 340},
            {"page": "/designs/turbine-blade", "views": 280},
            {"page": "/designs/heat-exchanger", "views": 230}
        ],
        bounce_rate=25.5,
        session_duration=245.7
    )


@router.get("/earnings/{user_id}", response_model=EarningsAnalyticsResponse)
async def get_earnings_analytics(
    user_id: int,
    period: str = Query(default="30_days", regex="^(7_days|30_days|90_days|1_year)$"),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get earnings analytics for a user."""
    
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get user earnings data
    stats = await crud_user_analytics.get_aggregated_user_stats(db, user_id, 30)
    total_earnings = stats.get('total_revenue', Decimal('0'))
    
    return EarningsAnalyticsResponse(
        user_id=user_id,
        period=period,
        total_earnings=total_earnings,
        earnings_trend=[
            {"date": "2025-10-25", "earnings": Decimal("45.00")},
            {"date": "2025-10-26", "earnings": Decimal("67.50")},
            {"date": "2025-10-27", "earnings": Decimal("112.25")},
            {"date": "2025-10-28", "earnings": Decimal("89.75")}
        ],
        earnings_by_category={
            "aerospace": Decimal("180.00"),
            "automotive": Decimal("120.00"),
            "industrial": Decimal("95.00")
        },
        top_earning_designs=[
            {"design_id": "design1", "name": "Aerospace Wing", "earnings": Decimal("240.00")},
            {"design_id": "design2", "name": "Turbine Blade", "earnings": Decimal("160.00")},
            {"design_id": "design3", "name": "Heat Exchanger", "earnings": Decimal("120.00")}
        ],
        payout_history=[
            {"date": "2025-10-01", "amount": Decimal("250.00"), "status": "completed"},
            {"date": "2025-09-01", "amount": Decimal("180.00"), "status": "completed"}
        ],
        pending_earnings=Decimal("95.75")
    )


@router.get("/summary/{user_id}")
async def get_analytics_summary(
    user_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a quick analytics summary for dashboard overview."""
    
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get basic stats
    stats = await crud_user_analytics.get_aggregated_user_stats(db, user_id, 30)
    user_designs = await design_asset_crud.get_seller_designs(db, user_id)
    
    return {
        "total_views": stats.get('total_views', 0),
        "total_sales": stats.get('total_sales', 0),
        "total_revenue": float(stats.get('total_revenue', Decimal('0'))),
        "active_listings": len([d for d in user_designs if d.status == "active"]),
        "conversion_rate": stats.get('customer_retention_rate', 0.0),
        "this_month_growth": 15.2,  # Mock value
        "trending_designs": 3,      # Mock value
        "new_customers": stats.get('new_customers', 0)
    }