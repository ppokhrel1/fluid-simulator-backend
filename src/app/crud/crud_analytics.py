"""CRUD operations for analytics models."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from datetime import datetime, date, timedelta
from decimal import Decimal

from ..models.analytics import DesignAnalytics, UserAnalytics


class CRUDDesignAnalytics:
    """CRUD operations for design analytics."""
    
    async def create_or_update_daily_stats(
        self,
        db: AsyncSession,
        design_id: str,
        analytics_date: date = None,
        views: int = 0,
        unique_viewers: int = 0,
        likes: int = 0,
        downloads: int = 0,
        revenue: Decimal = Decimal("0")
    ) -> DesignAnalytics:
        """Create or update daily analytics for a design."""
        if analytics_date is None:
            analytics_date = date.today()
        
        # Try to get existing record
        result = await db.execute(
            select(DesignAnalytics).where(
                and_(
                    DesignAnalytics.design_id == design_id,
                    DesignAnalytics.date == analytics_date
                )
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing record
            existing.views += views
            existing.unique_viewers += unique_viewers
            existing.likes += likes
            existing.downloads += downloads
            existing.revenue += revenue
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            # Create new record
            analytics = DesignAnalytics(
                design_id=design_id,
                date=analytics_date,
                views=views,
                unique_viewers=unique_viewers,
                likes=likes,
                downloads=downloads,
                revenue=revenue
            )
            db.add(analytics)
            await db.commit()
            await db.refresh(analytics)
            return analytics
    
    async def get_design_analytics(
        self,
        db: AsyncSession,
        design_id: str,
        start_date: date = None,
        end_date: date = None
    ) -> List[DesignAnalytics]:
        """Get analytics data for a design within date range."""
        if start_date is None:
            start_date = date.today() - timedelta(days=30)
        if end_date is None:
            end_date = date.today()
        
        result = await db.execute(
            select(DesignAnalytics)
            .where(
                and_(
                    DesignAnalytics.design_id == design_id,
                    DesignAnalytics.date >= start_date,
                    DesignAnalytics.date <= end_date
                )
            )
            .order_by(DesignAnalytics.date)
        )
        return result.scalars().all()
    
    async def get_aggregated_design_stats(
        self,
        db: AsyncSession,
        design_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get aggregated statistics for a design."""
        start_date = date.today() - timedelta(days=days)
        
        result = await db.execute(
            select(
                func.sum(DesignAnalytics.views).label('total_views'),
                func.sum(DesignAnalytics.unique_viewers).label('total_unique_viewers'),
                func.sum(DesignAnalytics.likes).label('total_likes'),
                func.sum(DesignAnalytics.downloads).label('total_downloads'),
                func.sum(DesignAnalytics.revenue).label('total_revenue'),
                func.avg(DesignAnalytics.views).label('avg_daily_views')
            )
            .where(
                and_(
                    DesignAnalytics.design_id == design_id,
                    DesignAnalytics.date >= start_date
                )
            )
        )
        
        row = result.first()
        if not row:
            return {
                'total_views': 0,
                'total_unique_viewers': 0,
                'total_likes': 0,
                'total_downloads': 0,
                'total_revenue': Decimal('0'),
                'avg_daily_views': 0,
                'conversion_rate': 0.0
            }
        
        total_views = row.total_views or 0
        total_downloads = row.total_downloads or 0
        conversion_rate = (total_downloads / total_views * 100) if total_views > 0 else 0.0
        
        return {
            'total_views': total_views,
            'total_unique_viewers': row.total_unique_viewers or 0,
            'total_likes': row.total_likes or 0,
            'total_downloads': total_downloads,
            'total_revenue': row.total_revenue or Decimal('0'),
            'avg_daily_views': float(row.avg_daily_views or 0),
            'conversion_rate': round(conversion_rate, 2)
        }


class CRUDUserAnalytics:
    """CRUD operations for user analytics."""
    
    async def create_or_update_daily_stats(
        self,
        db: AsyncSession,
        user_id: int,
        analytics_date: date = None,
        total_views: int = 0,
        total_sales: int = 0,
        total_revenue: Decimal = Decimal("0"),
        new_customers: int = 0,
        returning_customers: int = 0,
        analytics_data: Dict[str, Any] = None
    ) -> UserAnalytics:
        """Create or update daily analytics for a user."""
        if analytics_date is None:
            analytics_date = date.today()
        
        # Try to get existing record
        result = await db.execute(
            select(UserAnalytics).where(
                and_(
                    UserAnalytics.user_id == user_id,
                    UserAnalytics.date == analytics_date
                )
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing record
            existing.total_views += total_views
            existing.total_sales += total_sales
            existing.total_revenue += total_revenue
            existing.new_customers += new_customers
            existing.returning_customers += returning_customers
            if analytics_data:
                import json
                try:
                    current_data = json.loads(existing.analytics_data or "{}")
                    current_data.update(analytics_data)
                    existing.analytics_data = json.dumps(current_data)
                except json.JSONDecodeError:
                    existing.analytics_data = json.dumps(analytics_data)
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            # Create new record
            import json
            analytics = UserAnalytics(
                user_id=user_id,
                date=analytics_date,
                total_views=total_views,
                total_sales=total_sales,
                total_revenue=total_revenue,
                new_customers=new_customers,
                returning_customers=returning_customers,
                analytics_data=json.dumps(analytics_data or {})
            )
            db.add(analytics)
            await db.commit()
            await db.refresh(analytics)
            return analytics
    
    async def get_user_analytics(
        self,
        db: AsyncSession,
        user_id: int,
        start_date: date = None,
        end_date: date = None
    ) -> List[UserAnalytics]:
        """Get analytics data for a user within date range."""
        if start_date is None:
            start_date = date.today() - timedelta(days=30)
        if end_date is None:
            end_date = date.today()
        
        result = await db.execute(
            select(UserAnalytics)
            .where(
                and_(
                    UserAnalytics.user_id == user_id,
                    UserAnalytics.date >= start_date,
                    UserAnalytics.date <= end_date
                )
            )
            .order_by(UserAnalytics.date)
        )
        return result.scalars().all()
    
    async def get_aggregated_user_stats(
        self,
        db: AsyncSession,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get aggregated statistics for a user."""
        start_date = date.today() - timedelta(days=days)
        
        result = await db.execute(
            select(
                func.sum(UserAnalytics.total_views).label('total_views'),
                func.sum(UserAnalytics.total_sales).label('total_sales'),
                func.sum(UserAnalytics.total_revenue).label('total_revenue'),
                func.sum(UserAnalytics.new_customers).label('new_customers'),
                func.sum(UserAnalytics.returning_customers).label('returning_customers'),
                func.avg(UserAnalytics.total_revenue).label('avg_daily_revenue')
            )
            .where(
                and_(
                    UserAnalytics.user_id == user_id,
                    UserAnalytics.date >= start_date
                )
            )
        )
        
        row = result.first()
        if not row:
            return {
                'total_views': 0,
                'total_sales': 0,
                'total_revenue': Decimal('0'),
                'new_customers': 0,
                'returning_customers': 0,
                'avg_daily_revenue': 0.0,
                'average_order_value': 0.0,
                'customer_retention_rate': 0.0
            }
        
        total_sales = row.total_sales or 0
        total_revenue = row.total_revenue or Decimal('0')
        new_customers = row.new_customers or 0
        returning_customers = row.returning_customers or 0
        total_customers = new_customers + returning_customers
        
        average_order_value = float(total_revenue / total_sales) if total_sales > 0 else 0.0
        retention_rate = (returning_customers / total_customers * 100) if total_customers > 0 else 0.0
        
        return {
            'total_views': row.total_views or 0,
            'total_sales': total_sales,
            'total_revenue': total_revenue,
            'new_customers': new_customers,
            'returning_customers': returning_customers,
            'avg_daily_revenue': float(row.avg_daily_revenue or 0),
            'average_order_value': round(average_order_value, 2),
            'customer_retention_rate': round(retention_rate, 2)
        }


# Create instances
crud_design_analytics = CRUDDesignAnalytics()
crud_user_analytics = CRUDUserAnalytics()