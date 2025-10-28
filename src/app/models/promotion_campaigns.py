"""Promotion Campaigns Model for design promotion functionality."""

from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, DateTime, DECIMAL, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..core.db.database import Base


class PromotionCampaign(Base):
    """Promotion campaigns for design visibility boost."""
    
    __tablename__ = "promotion_campaigns"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    design_id = Column(String(255), ForeignKey("design_assets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Campaign owner
    campaign_name = Column(String(255), nullable=False)
    campaign_type = Column(String(100), nullable=False)  # featured, boost, sponsored, etc.
    duration_days = Column(Integer, nullable=False)
    budget = Column(DECIMAL(10, 2), nullable=True)
    status = Column(String(50), default="active")  # active, paused, completed, cancelled
    metrics = Column(String, default="{}")  # JSON as string for SQLite
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    # Relationships
    # design = relationship("DesignAsset", back_populates="promotion_campaigns")
    # user = relationship("User", back_populates="promotion_campaigns")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.duration_days and not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(days=self.duration_days)
    
    def __repr__(self):
        return f"<PromotionCampaign(id={self.id}, name={self.campaign_name}, status={self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Check if campaign is currently active."""
        now = datetime.utcnow()
        return (
            self.status == "active" 
            and now < self.expires_at 
            and now >= self.created_at
        )
    
    @property
    def days_remaining(self) -> int:
        """Calculate days remaining in campaign."""
        if not self.is_active:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def budget_spent(self) -> float:
        """Get budget spent from metrics."""
        try:
            import json
            metrics = json.loads(self.metrics or "{}")
            return float(metrics.get("budget_spent", 0))
        except (ValueError, TypeError, json.JSONDecodeError):
            return 0.0
    
    @property
    def impressions(self) -> int:
        """Get impression count from metrics."""
        try:
            import json
            metrics = json.loads(self.metrics or "{}")
            return int(metrics.get("impressions", 0))
        except (ValueError, TypeError, json.JSONDecodeError):
            return 0
    
    def update_metrics(self, new_metrics: dict):
        """Update campaign metrics."""
        try:
            import json
            current_metrics = json.loads(self.metrics or "{}")
            current_metrics.update(new_metrics)
            self.metrics = json.dumps(current_metrics)
        except (ValueError, TypeError, json.JSONDecodeError):
            import json
            self.metrics = json.dumps(new_metrics)
    
    def pause(self):
        """Pause the campaign."""
        self.status = "paused"
    
    def resume(self):
        """Resume the campaign."""
        if datetime.utcnow() < self.expires_at:
            self.status = "active"
    
    def complete(self):
        """Mark campaign as completed."""
        self.status = "completed"