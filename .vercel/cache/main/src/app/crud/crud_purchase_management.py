"""CRUD operations for purchase details and support tickets."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from datetime import datetime, timedelta
import uuid6 as uuid

from ..models.purchase_details import PurchaseDetails
from ..models.support_tickets import SupportTicket


class CRUDPurchaseDetails:
    """CRUD operations for purchase details."""
    
    async def create(
        self, 
        db: AsyncSession, 
        purchase_id: str,
        item_details: Dict[str, Any],
        download_links: List[str] = None,
        max_downloads: int = 5
    ) -> PurchaseDetails:
        """Create purchase details record."""
        purchase_details = PurchaseDetails(
            id=str(uuid.uuid4()),
            purchase_id=purchase_id,
            item_details=item_details,
            download_links=download_links or [],
            max_downloads=max_downloads,
            expires_at=datetime.utcnow() + timedelta(days=30)  # 30 day download window
        )
        db.add(purchase_details)
        await db.commit()
        await db.refresh(purchase_details)
        return purchase_details
    
    async def get_by_purchase_id(self, db: AsyncSession, purchase_id: str) -> Optional[PurchaseDetails]:
        """Get purchase details by purchase ID."""
        result = await db.execute(
            select(PurchaseDetails).where(PurchaseDetails.purchase_id == purchase_id)
        )
        return result.scalar_one_or_none()
    
    async def increment_download_count(self, db: AsyncSession, purchase_id: str) -> bool:
        """Increment download count and return success status."""
        purchase_details = await self.get_by_purchase_id(db, purchase_id)
        if not purchase_details or not purchase_details.can_download():
            return False
        
        purchase_details.download_count += 1
        await db.commit()
        return True
    
    async def extend_download_window(
        self, 
        db: AsyncSession, 
        purchase_id: str, 
        additional_days: int = 30
    ) -> bool:
        """Extend download window for a purchase."""
        purchase_details = await self.get_by_purchase_id(db, purchase_id)
        if not purchase_details:
            return False
        
        if purchase_details.expires_at:
            purchase_details.expires_at += timedelta(days=additional_days)
        else:
            purchase_details.expires_at = datetime.utcnow() + timedelta(days=additional_days)
        
        await db.commit()
        return True


class CRUDSupportTicket:
    """CRUD operations for support tickets."""
    
    async def create(
        self,
        db: AsyncSession,
        purchase_id: str,
        user_id: int,
        issue_type: str,
        subject: str,
        description: str,
        priority: str = "medium"
    ) -> SupportTicket:
        """Create a new support ticket."""
        ticket = SupportTicket(
            id=str(uuid.uuid4()),
            purchase_id=purchase_id,
            user_id=user_id,
            issue_type=issue_type,
            subject=subject,
            description=description,
            priority=priority
        )
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
        return ticket
    
    async def get_by_id(self, db: AsyncSession, ticket_id: str) -> Optional[SupportTicket]:
        """Get support ticket by ID."""
        result = await db.execute(
            select(SupportTicket).where(SupportTicket.id == ticket_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_tickets(
        self, 
        db: AsyncSession, 
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[SupportTicket]:
        """Get support tickets for a user."""
        query = select(SupportTicket).where(SupportTicket.user_id == user_id)
        
        if status:
            query = query.where(SupportTicket.status == status)
        
        query = query.order_by(SupportTicket.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_purchase_tickets(
        self, 
        db: AsyncSession, 
        purchase_id: str
    ) -> List[SupportTicket]:
        """Get all tickets for a specific purchase."""
        result = await db.execute(
            select(SupportTicket)
            .where(SupportTicket.purchase_id == purchase_id)
            .order_by(SupportTicket.created_at.desc())
        )
        return result.scalars().all()
    
    async def update_status(
        self, 
        db: AsyncSession, 
        ticket_id: str, 
        status: str,
        assigned_to: Optional[int] = None
    ) -> Optional[SupportTicket]:
        """Update ticket status and assignment."""
        ticket = await self.get_by_id(db, ticket_id)
        if not ticket:
            return None
        
        ticket.status = status
        ticket.updated_at = datetime.utcnow()
        
        if assigned_to is not None:
            ticket.assigned_to = assigned_to
        
        if status in ["resolved", "closed"]:
            ticket.resolved_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(ticket)
        return ticket
    
    async def get_open_tickets_count(self, db: AsyncSession, user_id: int) -> int:
        """Get count of open tickets for a user."""
        result = await db.execute(
            select(SupportTicket)
            .where(
                and_(
                    SupportTicket.user_id == user_id,
                    SupportTicket.status.in_(["open", "in_progress"])
                )
            )
        )
        return len(result.scalars().all())


# Create instances
crud_purchase_details = CRUDPurchaseDetails()
crud_support_ticket = CRUDSupportTicket()