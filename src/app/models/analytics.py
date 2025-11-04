"""Design Analytics Model for tracking design performance."""

from datetime import datetime, date
from typing import Optional # Recommended for Optional fields like created_at default
import uuid as uuid_pkg

from sqlalchemy import Integer, DateTime, Date, DECIMAL, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, Text # Import String and Text if needed in this file
from decimal import Decimal
from src.app.core.db.database import Base


class DesignAnalytics(Base):
    """Daily analytics data for designs."""
    
    __tablename__ = "design_analytics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # FIX: Changed String(255) to UUID(as_uuid=True) to match design_assets.id
    design_id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("design_assets.id"), 
        nullable=False
    )
    
    date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    views: Mapped[int] = mapped_column(Integer, default=0)
    unique_viewers: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    downloads: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Unique constraint on design_id and date
    __table_args__ = (UniqueConstraint('design_id', 'date', name='unique_design_date'),)
    
    # Relationships (Assuming DesignAsset model is available)
    # design = relationship("DesignAsset", back_populates="analytics")
    
    def __repr__(self):
        return f"<DesignAnalytics(design_id={self.design_id}, date={self.date}, views={self.views})>"
    
    @property
    def conversion_rate(self) -> float:
        """Calculate conversion rate from views to downloads."""
        if self.views == 0:
            return 0.0
        return round((self.downloads / self.views) * 100, 2)
    
    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate (likes per view)."""
        if self.views == 0:
            return 0.0
        return round((self.likes / self.views) * 100, 2)


class UserAnalytics(Base):
    """Daily analytics data for users."""
    
    __tablename__ = "user_analytics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    total_views: Mapped[int] = mapped_column(Integer, default=0)
    total_sales: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    new_customers: Mapped[int] = mapped_column(Integer, default=0)
    returning_customers: Mapped[int] = mapped_column(Integer, default=0)
    
    # Use String type for JSON data, consider using JSON type for PostgreSQL
    analytics_data: Mapped[str] = mapped_column(String, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Unique constraint on user_id and date
    __table_args__ = (UniqueConstraint('user_id', 'date', name='unique_user_date'),)
    
    # Relationships
    # user = relationship("User", back_populates="analytics")
    
    def __repr__(self):
        return f"<UserAnalytics(user_id={self.user_id}, date={self.date}, revenue={self.total_revenue})>"
    
    @property
    def average_order_value(self) -> float:
        """Calculate average order value."""
        if self.total_sales == 0:
            return 0.0
        return round(float(self.total_revenue) / self.total_sales, 2)
    
    @property
    def customer_retention_rate(self) -> float:
        """Calculate customer retention rate."""
        total_customers = self.new_customers + self.returning_customers
        if total_customers == 0:
            return 0.0
        return round((self.returning_customers / total_customers) * 100, 2)