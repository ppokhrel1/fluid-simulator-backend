"""Purchase management endpoints for Dashboard functionality."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.security import get_current_user
from ...models.user import User
from ...schemas.purchase_management import (
    PurchaseDetailsResponse,
    FileDownloadResponse,
    SupportTicketRequest,
    SupportTicketResponse,
    EnhancedPurchaseResponse
)
from ...crud import crud_purchase_details, crud_support_ticket
from ...crud.crud_commerce import sales_transaction_crud
import tempfile
import os
from datetime import datetime, timedelta

router = APIRouter(prefix="/purchases", tags=["Purchase Management"])


@router.get("/{purchase_id}/details", response_model=PurchaseDetailsResponse)
async def get_purchase_details(
    purchase_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a purchase."""
    
    # Get the purchase record
    purchase = await sales_transaction_crud.get_by_id(db, purchase_id)
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found"
        )
    
    # Verify ownership
    if str(purchase.userId) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this purchase"
        )
    
    # Get or create purchase details
    purchase_details = await crud_purchase_details.get_by_purchase_id(db, purchase_id)
    if not purchase_details:
        # Create basic purchase details if they don't exist
        purchase_details = await crud_purchase_details.create(
            db=db,
            purchase_id=purchase_id,
            item_details={"items": purchase.items or []},
            download_links=[]
        )
    
    # Build response
    return PurchaseDetailsResponse(
        id=purchase.id,
        purchase_date=purchase.purchaseDate.isoformat(),
        items=purchase.items or [],
        total=purchase.total,
        subtotal=purchase.total * 0.9,  # Assuming 10% tax
        tax=purchase.total * 0.1,
        status="completed",
        buyer_info={
            "user_id": current_user.id,
            "username": current_user.username,
            "email": current_user.email
        },
        seller_info={
            "seller_id": "marketplace",
            "seller_name": "Fluid Simulator Marketplace"
        },
        transaction_id=purchase.id,
        payment_method="credit_card",
        shipping_info=None
    )


@router.get("/{purchase_id}/download/{item_id}", response_model=FileDownloadResponse)
async def get_download_link(
    purchase_id: str,
    item_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get download link for a purchased item."""
    
    # Verify purchase ownership
    purchase = await sales_transaction_crud.get_by_id(db, purchase_id)
    if not purchase or str(purchase.userId) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found or access denied"
        )
    
    # Get purchase details
    purchase_details = await crud_purchase_details.get_by_purchase_id(db, purchase_id)
    if not purchase_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase details not found"
        )
    
    # Check if download is allowed
    if not purchase_details.can_download():
        if purchase_details.is_expired:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Download link has expired"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum downloads exceeded"
            )
    
    # Increment download count
    await crud_purchase_details.increment_download_count(db, purchase_id)
    
    # Generate download URL (in production, this would be a signed URL)
    download_url = f"https://storage.example.com/downloads/{purchase_id}/{item_id}"
    
    return FileDownloadResponse(
        file_url=download_url,
        filename=f"design_{item_id}.stl",
        file_size=1024000,  # 1MB example
        download_expires_at=(datetime.utcnow() + timedelta(hours=24)).isoformat(),
        download_count=purchase_details.download_count,
        max_downloads=purchase_details.max_downloads
    )


@router.post("/{purchase_id}/support", response_model=SupportTicketResponse)
async def create_support_ticket(
    purchase_id: str,
    ticket_request: SupportTicketRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a support ticket for a purchase."""
    
    # Verify purchase ownership
    purchase = await sales_transaction_crud.get_by_id(db, purchase_id)
    if not purchase or str(purchase.userId) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found or access denied"
        )
    
    # Create support ticket
    ticket = await crud_support_ticket.create(
        db=db,
        purchase_id=purchase_id,
        user_id=current_user.id,
        issue_type=ticket_request.issue_type,
        subject=ticket_request.subject,
        description=ticket_request.description,
        priority=ticket_request.priority
    )
    
    # Calculate estimated response time
    response_times = {
        "urgent": "2 hours",
        "high": "4 hours", 
        "medium": "24 hours",
        "low": "72 hours"
    }
    
    return SupportTicketResponse(
        ticket_id=ticket.id,
        status=ticket.status,
        created_at=ticket.created_at.isoformat(),
        estimated_response_time=response_times.get(ticket.priority, "24 hours")
    )


@router.get("/user/{user_id}", response_model=List[EnhancedPurchaseResponse])
async def get_user_purchases(
    user_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all purchases for a user with enhanced details."""
    
    # Verify access (users can only see their own purchases)
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get user purchases
    purchases = await sales_transaction_crud.get_user_transactions(db, user_id, limit)
    
    enhanced_purchases = []
    for purchase in purchases:
        # Get purchase details if they exist
        purchase_details = await crud_purchase_details.get_by_purchase_id(db, purchase.id)
        
        enhanced_purchase = EnhancedPurchaseResponse(
            id=purchase.id,
            items=[{
                "design_id": item.get("id", "unknown"),
                "design_name": item.get("name", "Unknown Design"),
                "price": item.get("price", 0),
                "quantity": 1,
                "seller_id": item.get("seller_id", 1),
                "file_urls": []
            } for item in (purchase.items or [])],
            total=purchase.total,
            subtotal=purchase.total * 0.9,
            tax=purchase.total * 0.1,
            purchaseDate=purchase.purchaseDate,
            userId=str(purchase.userId),
            status="completed",
            payment_method="credit_card",
            transaction_id=purchase.id,
            download_links=purchase_details.download_links if purchase_details else [],
            support_eligible=True,
            refund_eligible=False
        )
        enhanced_purchases.append(enhanced_purchase)
    
    return enhanced_purchases


@router.get("/{purchase_id}/support-tickets")
async def get_purchase_support_tickets(
    purchase_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all support tickets for a purchase."""
    
    # Verify purchase ownership
    purchase = await sales_transaction_crud.get_by_id(db, purchase_id)
    if not purchase or str(purchase.userId) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found or access denied"
        )
    
    # Get tickets
    tickets = await crud_support_ticket.get_purchase_tickets(db, purchase_id)
    
    return [
        {
            "id": ticket.id,
            "issue_type": ticket.issue_type,
            "subject": ticket.subject,
            "status": ticket.status,
            "priority": ticket.priority,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat()
        }
        for ticket in tickets
    ]