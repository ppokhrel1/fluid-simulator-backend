"""Advanced tools endpoints for Dashboard functionality."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from src.app.core.db.database import async_get_db
from src.app.core.security import get_current_user
from src.app.models.user import User
from src.app.schemas.advanced_tools import (
    PricingAnalysisRequest,
    PricingAnalysisResponse,
    MarketAnalysis,
    ReviewManagementResponse,
    ReviewSummary,
    ReviewDetails,
    ReviewResponseRequest,
    ReviewResponseResponse,
    PromotionCampaignRequest,
    PromotionCampaignResponse,
    CustomerAnalyticsResponse,
    CustomerSegment,
    CustomerBehavior,
    CompetitiveAnalysisResponse,
    CompetitorData
)
from src.app.crud import crud_promotion_campaign
from src.app.crud.crud_commerce import design_asset_crud

def extract_list(result):
    # tuple: (list, count)
    if isinstance(result, tuple):
        return result[0]

    # dict pagination shape: {"data": [...], "total_count": N}
    if isinstance(result, dict) and "data" in result:
        return result["data"]

    # otherwise return as-is (if it's already a list)
    return result

router = APIRouter(prefix="/tools", tags=["Advanced Tools"])


@router.get("/pricing/{user_id}")
async def get_pricing_overview(
    user_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pricing overview for user's designs."""
    
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get user's designs
    user_designs = await design_asset_crud.get_seller_designs(db, user_id)
    
    # Calculate pricing statistics
    if not user_designs:
        return {
            "total_designs": 0,
            "average_price": 0.0,
            "price_range": {"min": 0.0, "max": 0.0},
            "underpriced_designs": 0,
            "overpriced_designs": 0,
            "optimally_priced_designs": 0
        }
    
    prices = [float(design.price) for design in user_designs]
    avg_price = sum(prices) / len(prices)
    
    return {
        "total_designs": len(user_designs),
        "average_price": round(avg_price, 2),
        "price_range": {
            "min": min(prices),
            "max": max(prices)
        },
        "underpriced_designs": len([p for p in prices if p < avg_price * 0.8]),
        "overpriced_designs": len([p for p in prices if p > avg_price * 1.2]),
        "optimally_priced_designs": len([p for p in prices if avg_price * 0.8 <= p <= avg_price * 1.2]),
        "categories": list(set(design.category for design in user_designs)),
        "recommendations": [
            "Consider adjusting prices 15% below market average",
            "Bundle complementary designs for better value",
            "Seasonal pricing adjustments can increase sales"
        ]
    }


@router.post("/pricing/analyze", response_model=List[PricingAnalysisResponse])
async def analyze_pricing(
    request: PricingAnalysisRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze pricing for specific designs."""
    
    results = []
    
    for design_id in request.design_ids:
        # Verify ownership
        design = await design_asset_crud.get(db, id=design_id)
        if not design or design.seller_id != current_user.id:
            continue
        
        # Mock market analysis (in production, this would use real market data)
        market_analysis = MarketAnalysis(
            competitor_prices=[
                {"design": "Similar Design A", "price": float(design.price) * 0.9},
                {"design": "Similar Design B", "price": float(design.price) * 1.1},
                {"design": "Similar Design C", "price": float(design.price) * 1.05}
            ],
            price_trend="rising",
            demand_level="high",
            market_saturation=0.65,
            recommended_price_range={
                "min": design.price * Decimal("0.95"),
                "max": design.price * Decimal("1.15")
            }
        )
        
        # Calculate suggested price
        market_avg = sum(comp["price"] for comp in market_analysis.competitor_prices) / len(market_analysis.competitor_prices)
        suggested_price = Decimal(str(market_avg))
        
        analysis = PricingAnalysisResponse(
            design_id=design_id,
            current_price=design.price,
            suggested_price=suggested_price,
            price_confidence=0.85,
            market_analysis=market_analysis,
            optimization_suggestions=[
                "Price is within optimal range for your category",
                "Consider promotional pricing to increase visibility",
                "Bundle with complementary designs for higher value"
            ],
            potential_revenue_impact={
                "current_monthly": design.price * Decimal("10"),  # Mock sales volume
                "projected_monthly": suggested_price * Decimal("12")
            }
        )
        
        results.append(analysis)
    
    return extract_list(results)


@router.get("/reviews/{user_id}", response_model=ReviewManagementResponse)
async def get_review_management(
    user_id: int,
    status: Optional[str] = Query(None, regex="^(all|needs_response|responded)$"),
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get review management data for user's designs."""
    
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Mock review data (in production, this would come from a reviews table)
    from datetime import datetime, timedelta
    
    mock_reviews = [
        ReviewDetails(
            id="review_1",
            design_id="design_1",
            design_name="Aerospace Wing",
            reviewer_name="John D.",
            rating=5,
            comment="Excellent quality design! Perfect for our aerospace project.",
            created_at=datetime.utcnow() - timedelta(days=2),
            response=None,
            response_date=None,
            needs_response=True,
            sentiment="positive"
        ),
        ReviewDetails(
            id="review_2",
            design_id="design_2",
            design_name="Turbine Blade",
            reviewer_name="Sarah M.",
            rating=4,
            comment="Good design, but could use better documentation.",
            created_at=datetime.utcnow() - timedelta(days=5),
            response="Thank you for the feedback! We've updated the documentation.",
            response_date=datetime.utcnow() - timedelta(days=3),
            needs_response=False,
            sentiment="positive"
        ),
        ReviewDetails(
            id="review_3",
            design_id="design_3",
            design_name="Heat Exchanger",
            reviewer_name="Mike R.",
            rating=3,
            comment="Design works but took longer to implement than expected.",
            created_at=datetime.utcnow() - timedelta(days=7),
            response=None,
            response_date=None,
            needs_response=True,
            sentiment="neutral"
        )
    ]
    
    # Filter by status if specified
    if status == "needs_response":
        mock_reviews = [r for r in mock_reviews if r.needs_response]
    elif status == "responded":
        mock_reviews = [r for r in mock_reviews if not r.needs_response and r.response]
    
    # Limit results
    mock_reviews = mock_reviews[:limit]
    
    # Calculate summary
    all_reviews = mock_reviews  # In production, get all reviews for summary
    total_reviews = len(all_reviews)
    avg_rating = sum(r.rating for r in all_reviews) / total_reviews if total_reviews > 0 else 0
    
    rating_distribution = {str(i): 0 for i in range(1, 6)}
    for review in all_reviews:
        rating_distribution[str(review.rating)] += 1
    
    summary = ReviewSummary(
        average_rating=round(avg_rating, 2),
        total_reviews=total_reviews,
        rating_distribution=rating_distribution,
        response_needed=len([r for r in all_reviews if r.needs_response]),
        sentiment_analysis={
            "positive": 0.65,
            "neutral": 0.25,
            "negative": 0.10
        }
    )
    
    return ReviewManagementResponse(
        reviews=mock_reviews,
        summary=summary,
        actionable_insights=[
            "3 reviews need responses - responding within 24 hours improves customer satisfaction",
            "Overall sentiment is positive (65%) - highlight positive aspects in marketing",
            "Documentation mentioned in feedback - consider improving design documentation"
        ]
    )


@router.put("/reviews/{review_id}/respond", response_model=ReviewResponseResponse)
async def respond_to_review(
    review_id: str,
    response_data: ReviewResponseRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Respond to a customer review."""
    
    # In production, verify the review belongs to user's design
    # For now, mock successful response
    from datetime import datetime
    
    return ReviewResponseResponse(
        review_id=review_id,
        response=response_data.response,
        response_date=datetime.utcnow(),
        status="published" if response_data.is_public else "private",
        message="Response published successfully"
    )


@router.post("/promotion/campaign", response_model=PromotionCampaignResponse)
async def create_promotion_campaign(
    campaign_data: PromotionCampaignRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new promotion campaign."""
    
    # Verify ownership of all designs
    for design_id in campaign_data.design_ids:
        design = await design_asset_crud.get(db, id=design_id)
        if not design or design.seller_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to design {design_id}"
            )
    
    # Create campaign for the first design (in production, handle multiple designs)
    primary_design_id = campaign_data.design_ids[0]
    
    campaign = await crud_promotion_campaign.create(
        db=db,
        design_id=primary_design_id,
        user_id=current_user.id,
        campaign_name=campaign_data.campaign_name,
        campaign_type=campaign_data.campaign_type,
        duration_days=campaign_data.duration,
        budget=campaign_data.budget
    )
    
    # Calculate estimates (mock values)
    estimated_reach = int(campaign_data.budget * 10)  # $1 = 10 impressions
    estimated_clicks = int(estimated_reach * 0.02)   # 2% CTR
    estimated_conversions = int(estimated_clicks * 0.05)  # 5% conversion rate
    
    return PromotionCampaignResponse(
        campaign_id=campaign.id,
        campaign_name=campaign.campaign_name,
        design_ids=campaign_data.design_ids,
        campaign_type=campaign.campaign_type,
        duration=campaign.duration_days,
        budget=campaign.budget,
        status=campaign.status,
        estimated_reach=estimated_reach,
        estimated_clicks=estimated_clicks,
        estimated_conversions=estimated_conversions,
        created_at=campaign.created_at,
        expires_at=campaign.expires_at
    )


@router.get("/customer-analytics/{user_id}", response_model=CustomerAnalyticsResponse)
async def get_customer_analytics(
    user_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get customer analytics for a user's designs."""
    
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Mock customer analytics data
    customer_segments = [
        CustomerSegment(
            segment_name="Professional Engineers",
            customer_count=45,
            total_revenue=Decimal("1250.00"),
            average_order_value=Decimal("27.78"),
            repeat_purchase_rate=0.67,
            characteristics=["High-value purchases", "Technical designs", "Aerospace focus"]
        ),
        CustomerSegment(
            segment_name="Hobbyist Makers",
            customer_count=128,
            total_revenue=Decimal("892.50"),
            average_order_value=Decimal("6.97"),
            repeat_purchase_rate=0.23,
            characteristics=["Price-sensitive", "Educational designs", "Small quantities"]
        ),
        CustomerSegment(
            segment_name="Small Businesses",
            customer_count=32,
            total_revenue=Decimal("1680.00"),
            average_order_value=Decimal("52.50"),
            repeat_purchase_rate=0.81,
            characteristics=["Bulk purchases", "Industrial designs", "Regular orders"]
        )
    ]
    
    customer_behavior = CustomerBehavior(
        purchase_patterns={
            "peak_hours": [9, 10, 14, 15, 16],
            "peak_days": ["Monday", "Tuesday", "Wednesday"],
            "seasonal_trends": {"Q1": 0.85, "Q2": 1.15, "Q3": 0.95, "Q4": 1.25}
        },
        preferred_categories=["Aerospace", "Automotive", "Industrial"],
        seasonal_trends={
            "spring": {"increase": 15, "popular_categories": ["Automotive"]},
            "summer": {"decrease": 5, "popular_categories": ["Industrial"]},
            "fall": {"increase": 10, "popular_categories": ["Aerospace"]},
            "winter": {"increase": 25, "popular_categories": ["All"]}
        },
        price_sensitivity="medium",
        loyalty_score=7.2
    )
    
    return CustomerAnalyticsResponse(
        user_id=user_id,
        total_customers=205,
        new_customers_this_month=23,
        returning_customers=45,
        customer_segments=customer_segments,
        customer_behavior=customer_behavior,
        churn_risk={
            "high_risk": 12,
            "medium_risk": 28,
            "low_risk": 165,
            "factors": ["Long time since last purchase", "Price increases", "New competitors"]
        },
        recommendations=[
            "Focus marketing on Professional Engineers segment (highest value)",
            "Create loyalty program for Small Businesses (highest retention)",
            "Develop lower-priced designs for Hobbyist Makers segment",
            "Consider seasonal promotions in Q4 for maximum impact"
        ]
    )


@router.get("/competitive-analysis/{user_id}")
async def get_competitive_analysis(
    user_id: int,
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get competitive analysis for user's design category."""
    
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Mock competitive analysis data
    competitors = [
        CompetitorData(
            competitor_name="TechDesigns Pro",
            similar_designs_count=45,
            average_price=Decimal("28.50"),
            market_share_estimate=0.22,
            strengths=["Premium quality", "Fast delivery", "Good support"],
            weaknesses=["Higher prices", "Limited categories"]
        ),
        CompetitorData(
            competitor_name="CAD Marketplace",
            similar_designs_count=89,
            average_price=Decimal("15.75"),
            market_share_estimate=0.35,
            strengths=["Large selection", "Competitive pricing", "User reviews"],
            weaknesses=["Quality inconsistent", "Slow support"]
        ),
        CompetitorData(
            competitor_name="Engineering Hub",
            similar_designs_count=23,
            average_price=Decimal("45.00"),
            market_share_estimate=0.15,
            strengths=["Specialized designs", "Expert validation", "Premium service"],
            weaknesses=["Very expensive", "Limited audience"]
        )
    ]
    
    return CompetitiveAnalysisResponse(
        user_id=user_id,
        category=category or "Aerospace",
        competitors=competitors,
        market_position="challenger",
        competitive_advantages=[
            "Specialized aerospace focus",
            "Competitive pricing with quality",
            "Good customer response time",
            "Growing design portfolio"
        ],
        improvement_opportunities=[
            "Expand design portfolio to match CAD Marketplace",
            "Develop premium tier to compete with Engineering Hub",
            "Improve marketing to increase market share",
            "Add customer review system"
        ],
        market_trends={
            "growth_rate": 0.15,
            "popular_categories": ["Aerospace", "Automotive", "Industrial"],
            "pricing_trends": "stable_to_rising",
            "customer_preferences": ["Quality over price", "Fast delivery", "Good documentation"]
        }
    )