"""Design Analytics Model for tracking design performance."""

from datetime import datetime, date
from sqlalchemy import Column, String, Integer, DateTime, Date, DECIMAL, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey

from ..core.db.database import Base


class DesignAnalytics(Base):
    """Daily analytics data for designs."""
    
    __tablename__ = "design_analytics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    design_id = Column(String(255), ForeignKey("design_assets.id"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    views = Column(Integer, default=0)
    unique_viewers = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    downloads = Column(Integer, default=0)
    revenue = Column(DECIMAL(10, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Unique constraint on design_id and date
    __table_args__ = (UniqueConstraint('design_id', 'date', name='unique_design_date'),)
    
    # Relationships
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
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    total_views = Column(Integer, default=0)
    total_sales = Column(Integer, default=0)
    total_revenue = Column(DECIMAL(10, 2), default=0)
    new_customers = Column(Integer, default=0)
    returning_customers = Column(Integer, default=0)
    analytics_data = Column(String, default="{}")  # JSON data as string for SQLite
    created_at = Column(DateTime, default=datetime.utcnow)
    
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