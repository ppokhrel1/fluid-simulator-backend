"""CRUD operations for promotion campaigns."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import json

from src.app.models.promotion_campaigns import PromotionCampaign


class CRUDPromotionCampaign:
    """CRUD operations for promotion campaigns."""
    
    async def create(
        self,
        db: AsyncSession,
        design_id: str,
        user_id: int,
        campaign_name: str,
        campaign_type: str,
        duration_days: int,
        budget: Decimal = None
    ) -> PromotionCampaign:
        """Create a new promotion campaign."""
        campaign = PromotionCampaign(
            id=str(uuid.uuid4()),
            design_id=design_id,
            user_id=user_id,
            campaign_name=campaign_name,
            campaign_type=campaign_type,
            duration_days=duration_days,
            budget=budget,
            expires_at=datetime.utcnow() + timedelta(days=duration_days)
        )
        
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        return campaign
    
    async def get_by_id(self, db: AsyncSession, campaign_id: str) -> Optional[PromotionCampaign]:
        """Get campaign by ID."""
        result = await db.execute(
            select(PromotionCampaign).where(PromotionCampaign.id == campaign_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_campaigns(
        self,
        db: AsyncSession,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[PromotionCampaign]:
        """Get campaigns for a user."""
        query = select(PromotionCampaign).where(PromotionCampaign.user_id == user_id)
        
        if status:
            query = query.where(PromotionCampaign.status == status)
        
        query = query.order_by(PromotionCampaign.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_design_campaigns(
        self,
        db: AsyncSession,
        design_id: str,
        active_only: bool = False
    ) -> List[PromotionCampaign]:
        """Get campaigns for a specific design."""
        query = select(PromotionCampaign).where(PromotionCampaign.design_id == design_id)
        
        if active_only:
            query = query.where(
                and_(
                    PromotionCampaign.status == "active",
                    PromotionCampaign.expires_at > datetime.utcnow()
                )
            )
        
        query = query.order_by(PromotionCampaign.created_at.desc())
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_active_campaigns(
        self,
        db: AsyncSession,
        campaign_type: Optional[str] = None
    ) -> List[PromotionCampaign]:
        """Get all active campaigns."""
        query = select(PromotionCampaign).where(
            and_(
                PromotionCampaign.status == "active",
                PromotionCampaign.expires_at > datetime.utcnow()
            )
        )
        
        if campaign_type:
            query = query.where(PromotionCampaign.campaign_type == campaign_type)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update_status(
        self,
        db: AsyncSession,
        campaign_id: str,
        status: str
    ) -> Optional[PromotionCampaign]:
        """Update campaign status."""
        campaign = await self.get_by_id(db, campaign_id)
        if not campaign:
            return None
        
        campaign.status = status
        
        if status == "completed":
            campaign.complete()
        elif status == "paused":
            campaign.pause()
        elif status == "active" and campaign.status == "paused":
            campaign.resume()
        
        await db.commit()
        await db.refresh(campaign)
        return campaign
    
    async def update_metrics(
        self,
        db: AsyncSession,
        campaign_id: str,
        metrics: Dict[str, Any]
    ) -> Optional[PromotionCampaign]:
        """Update campaign metrics."""
        campaign = await self.get_by_id(db, campaign_id)
        if not campaign:
            return None
        
        campaign.update_metrics(metrics)
        await db.commit()
        await db.refresh(campaign)
        return campaign
    
    async def increment_impressions(
        self,
        db: AsyncSession,
        campaign_id: str,
        impressions: int = 1
    ) -> bool:
        """Increment impression count for campaign."""
        campaign = await self.get_by_id(db, campaign_id)
        if not campaign or not campaign.is_active:
            return False
        
        try:
            current_metrics = json.loads(campaign.metrics or "{}")
            current_metrics["impressions"] = current_metrics.get("impressions", 0) + impressions
            campaign.metrics = json.dumps(current_metrics)
            await db.commit()
            return True
        except json.JSONDecodeError:
            return False
    
    async def record_click(
        self,
        db: AsyncSession,
        campaign_id: str,
        user_id: Optional[int] = None
    ) -> bool:
        """Record a click on promoted content."""
        campaign = await self.get_by_id(db, campaign_id)
        if not campaign or not campaign.is_active:
            return False
        
        try:
            current_metrics = json.loads(campaign.metrics or "{}")
            current_metrics["clicks"] = current_metrics.get("clicks", 0) + 1
            if user_id:
                clicked_users = current_metrics.get("clicked_users", [])
                if user_id not in clicked_users:
                    clicked_users.append(user_id)
                    current_metrics["clicked_users"] = clicked_users
                    current_metrics["unique_clicks"] = len(clicked_users)
            
            campaign.metrics = json.dumps(current_metrics)
            await db.commit()
            return True
        except json.JSONDecodeError:
            return False
    
    async def record_conversion(
        self,
        db: AsyncSession,
        campaign_id: str,
        conversion_value: Decimal = None
    ) -> bool:
        """Record a conversion (purchase) from promoted content."""
        campaign = await self.get_by_id(db, campaign_id)
        if not campaign:
            return False
        
        try:
            current_metrics = json.loads(campaign.metrics or "{}")
            current_metrics["conversions"] = current_metrics.get("conversions", 0) + 1
            if conversion_value:
                current_metrics["conversion_value"] = (
                    current_metrics.get("conversion_value", 0) + float(conversion_value)
                )
            
            campaign.metrics = json.dumps(current_metrics)
            await db.commit()
            return True
        except json.JSONDecodeError:
            return False
    
    async def get_expired_campaigns(self, db: AsyncSession) -> List[PromotionCampaign]:
        """Get campaigns that have expired but are still marked as active."""
        result = await db.execute(
            select(PromotionCampaign).where(
                and_(
                    PromotionCampaign.status == "active",
                    PromotionCampaign.expires_at <= datetime.utcnow()
                )
            )
        )
        return result.scalars().all()
    
    async def cleanup_expired_campaigns(self, db: AsyncSession) -> int:
        """Mark expired campaigns as completed and return count."""
        expired_campaigns = await self.get_expired_campaigns(db)
        count = 0
        
        for campaign in expired_campaigns:
            campaign.complete()
            count += 1
        
        if count > 0:
            await db.commit()
        
        return count
    
    async def get_campaign_performance(
        self,
        db: AsyncSession,
        campaign_id: str
    ) -> Dict[str, Any]:
        """Get detailed performance metrics for a campaign."""
        campaign = await self.get_by_id(db, campaign_id)
        if not campaign:
            return {}
        
        try:
            metrics = json.loads(campaign.metrics or "{}")
            
            impressions = metrics.get("impressions", 0)
            clicks = metrics.get("clicks", 0)
            unique_clicks = metrics.get("unique_clicks", 0)
            conversions = metrics.get("conversions", 0)
            conversion_value = metrics.get("conversion_value", 0)
            
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
            cost_per_click = (float(campaign.budget_spent) / clicks) if clicks > 0 and campaign.budget else 0
            roi = ((conversion_value - float(campaign.budget_spent)) / float(campaign.budget_spent) * 100) if campaign.budget and campaign.budget_spent > 0 else 0
            
            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign.campaign_name,
                "status": campaign.status,
                "days_remaining": campaign.days_remaining,
                "impressions": impressions,
                "clicks": clicks,
                "unique_clicks": unique_clicks,
                "conversions": conversions,
                "conversion_value": conversion_value,
                "click_through_rate": round(ctr, 2),
                "conversion_rate": round(conversion_rate, 2),
                "cost_per_click": round(cost_per_click, 2),
                "return_on_investment": round(roi, 2),
                "budget": float(campaign.budget) if campaign.budget else 0,
                "budget_spent": campaign.budget_spent
            }
        except json.JSONDecodeError:
            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign.campaign_name,
                "status": campaign.status,
                "error": "Invalid metrics data"
            }


# Create instance
crud_promotion_campaign = CRUDPromotionCampaign()