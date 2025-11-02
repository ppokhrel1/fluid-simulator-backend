"""Support Tickets Model for customer support functionality."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import uuid as uuid_pkg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class SupportTicket(Base):
    """Support tickets for purchase-related issues."""
    
    __tablename__ = "support_tickets"
    
    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid_pkg.uuid4
    )
    
    transaction_id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("sales_transactions.id"), 
        nullable=False
    )
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    issue_type = Column(String(100), nullable=False)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="open")  # open, in_progress, resolved, closed
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    assigned_to = Column(Integer, ForeignKey("user.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    # user = relationship("User", foreign_keys=[user_id], back_populates="support_tickets")
    # assignee = relationship("User", foreign_keys=[assigned_to])
    # purchase = relationship("Purchase", back_populates="support_tickets")
    
    def __repr__(self):
        return f"<SupportTicket(id={self.id}, subject={self.subject}, status={self.status})>"
    
    @property
    def is_resolved(self) -> bool:
        """Check if ticket is resolved."""
        return self.status in ["resolved", "closed"]
    
    @property
    def response_time_hours(self) -> int:
        """Calculate estimated response time based on priority."""
        priority_times = {
            "urgent": 2,
            "high": 4,
            "medium": 24,
            "low": 72
        }
        return priority_times.get(self.priority, 24)
    
    def mark_resolved(self):
        """Mark ticket as resolved."""
        self.status = "resolved"
        self.resolved_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()