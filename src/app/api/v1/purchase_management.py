"""Purchase management endpoints for Dashboard functionality."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import json

from src.app.core.db.database import async_get_db
from src.app.core.security import get_current_user
from src.app.core.config import AppSettings
from src.app.models.user import User
from src.app.schemas.purchase_management import (
    PurchaseDetailsResponse,
    FileDownloadResponse,
    SupportTicketRequest,
    SupportTicketResponse,
    EnhancedPurchaseResponse,
    PurchaseItem
)
from src.app.crud import crud_purchase_details, crud_support_ticket, crud_payment_transactions
from src.app.crud.crud_commerce import sales_transaction_crud
from src.app.api.services import FileService
from src.app.api.services.storage_service import StorageService

router = APIRouter(prefix="/purchases", tags=["Purchase Management"])
settings = AppSettings()


def extract_list(result):
    # tuple: (list, count)
    if isinstance(result, tuple):
        return result[0]

    # dict pagination shape: {"data": [...], "total_count": N}
    if isinstance(result, dict) and "data" in result:
        return result["data"]

    # otherwise return as-is (if it's already a list)
    return result


@router.get("/{purchase_id}/details", response_model=PurchaseDetailsResponse)
async def get_purchase_details(
    purchase_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a purchase."""
    
    # Get the purchase record from sales transactions
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
    
    # Get payment transaction details
    payment_transaction = await crud_payment_transactions.get_by_stripe_id(
        db, purchase.stripe_payment_intent_id
    )
    
    # Get or create purchase details
    purchase_details = await crud_purchase_details.get_by_purchase_id(db, purchase_id)
    if not purchase_details:
        # Create detailed purchase record
        purchase_details = await crud_purchase_details.create(
            db=db,
            purchase_id=purchase_id,
            item_details={
                "items": purchase.items or [],
                "stripe_payment_intent_id": purchase.stripe_payment_intent_id,
                "total_amount": float(purchase.total),
                "currency": "usd"
            },
            download_links=[],
            metadata={
                "user_id": current_user.id,
                "username": current_user.username,
                "purchase_date": purchase.purchaseDate.isoformat()
            }
        )
    
    # Calculate tax and subtotal (use actual values if available)
    tax_rate = 0.1  # 10% tax
    subtotal = float(purchase.total) / (1 + tax_rate)
    tax = float(purchase.total) - subtotal
    
    # Build buyer info
    buyer_info = {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }
    
    # Build seller info from items
    seller_info = {}
    if purchase.items and len(purchase.items) > 0:
        first_item = purchase.items[0]
        seller_info = {
            "seller_id": first_item.get("seller_id", "marketplace"),
            "seller_name": first_item.get("seller_name", "Fluid Simulator Marketplace")
        }
    else:
        seller_info = {
            "seller_id": "marketplace",
            "seller_name": "Fluid Simulator Marketplace"
        }
    
    return PurchaseDetailsResponse(
        id=purchase.id,
        purchase_date=purchase.purchaseDate.isoformat(),
        items=purchase.items or [],
        total=purchase.total,
        subtotal=subtotal,
        tax=tax,
        status=purchase.status or "completed",
        buyer_info=buyer_info,
        seller_info=seller_info,
        transaction_id=purchase.id,
        payment_method=payment_transaction.metadata.get("payment_method", "card") if payment_transaction else "card",
        shipping_info=None
    )


@router.get("/{purchase_id}/download/{item_id}", response_model=FileDownloadResponse)
async def get_download_link(
    purchase_id: str,
    item_id: str,
    background_tasks: BackgroundTasks,
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
    if not await _can_download(purchase_details):
        if await _is_download_expired(purchase_details):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Download link has expired"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum downloads exceeded"
            )
    
    # Find the specific item in purchase
    item_data = None
    for item in purchase.items or []:
        if item.get("id") == item_id or item.get("design_id") == item_id:
            item_data = item
            break
    
    if not item_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in purchase"
        )
    
    # Generate secure download URL using StorageService
    storage_service = StorageService()
    try:
        # Get file path from item data or generate it
        file_path = item_data.get("file_path") or f"designs/{item_id}/model.stl"
        
        # Create signed download URL (expires in 24 hours)
        download_url = await storage_service.create_signed_download_url(
            file_path=file_path,
            expires_in=86400  # 24 hours
        )
        
        # Get file info for response
        file_info = await storage_service.get_file_info(file_path)
        
    except Exception as e:
        # Fallback to basic URL if storage service fails
        download_url = f"/api/v1/files/download/{item_id}"
        file_info = {"size": 1024000}  # Default 1MB
    
    # Increment download count in background
    background_tasks.add_task(
        crud_purchase_details.increment_download_count,
        db, purchase_id, item_id
    )
    
    # Update download links in purchase details
    current_links = purchase_details.download_links or []
    new_download_record = {
        "item_id": item_id,
        "downloaded_at": datetime.utcnow().isoformat(),
        "download_count": (purchase_details.download_count or 0) + 1,
        "ip_address": "tracked_in_background"  # You would get this from request
    }
    current_links.append(new_download_record)
    
    await crud_purchase_details.update_download_links(
        db, purchase_id, current_links
    )
    
    return FileDownloadResponse(
        file_url=download_url,
        filename=item_data.get("filename", f"design_{item_id}.stl"),
        file_size=file_info.get("size", 1024000),
        download_expires_at=(datetime.utcnow() + timedelta(hours=24)).isoformat(),
        download_count=purchase_details.download_count or 0,
        max_downloads=purchase_details.max_downloads or 5
    )


@router.post("/{purchase_id}/support", response_model=SupportTicketResponse)
async def create_support_ticket(
    purchase_id: str,
    ticket_request: SupportTicketRequest,
    background_tasks: BackgroundTasks,
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
    
    # Validate that purchase is eligible for support
    if not await _is_support_eligible(purchase):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This purchase is not eligible for support"
        )
    
    # Create support ticket
    ticket = await crud_support_ticket.create(
        db=db,
        purchase_id=purchase_id,
        user_id=current_user.id,
        issue_type=ticket_request.issue_type,
        subject=ticket_request.subject,
        description=ticket_request.description,
        priority=ticket_request.priority,
        attachments=ticket_request.attachments
    )
    
    # Send notification in background
    background_tasks.add_task(
        _send_support_notification,
        ticket, current_user, purchase
    )
    
    # Calculate estimated response time based on priority
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
    offset: int = 0,
    status_filter: Optional[str] = None,
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
    
    # Get user purchases with filtering
    purchases = await sales_transaction_crud.get_user_transactions(
        db, user_id, limit, offset, status_filter
    )
    
    enhanced_purchases = []
    for purchase in purchases:
        # Get purchase details
        purchase_details = await crud_purchase_details.get_by_purchase_id(db, purchase.id)
        
        # Get payment transaction for additional details
        payment_transaction = None
        if purchase.stripe_payment_intent_id:
            payment_transaction = await crud_payment_transactions.get_by_stripe_id(
                db, purchase.stripe_payment_intent_id
            )
        
        # Build purchase items
        purchase_items = []
        for item in (purchase.items or []):
            purchase_items.append(PurchaseItem(
                design_id=item.get("id", "unknown"),
                design_name=item.get("name", "Unknown Design"),
                price=item.get("price", 0),
                quantity=item.get("quantity", 1),
                seller_id=item.get("seller_id", 1),
                file_urls=item.get("file_urls", [])
            ))
        
        # Calculate tax and subtotal
        tax_rate = 0.1
        subtotal = float(purchase.total) / (1 + tax_rate)
        tax = float(purchase.total) - subtotal
        
        # Determine support and refund eligibility
        support_eligible = await _is_support_eligible(purchase)
        refund_eligible = await _is_refund_eligible(purchase, payment_transaction)
        
        enhanced_purchase = EnhancedPurchaseResponse(
            id=purchase.id,
            items=purchase_items,
            total=purchase.total,
            subtotal=subtotal,
            tax=tax,
            purchaseDate=purchase.purchaseDate,
            userId=str(purchase.userId),
            status=purchase.status or "completed",
            payment_method=payment_transaction.metadata.get("payment_method", "card") if payment_transaction else "card",
            transaction_id=purchase.id,
            download_links=purchase_details.download_links if purchase_details else [],
            support_eligible=support_eligible,
            refund_eligible=refund_eligible
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
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "attachments": ticket.attachments or [],
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
            "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None
        }
        for ticket in tickets
    ]


@router.get("/{purchase_id}/refund-eligibility")
async def check_refund_eligibility(
    purchase_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if a purchase is eligible for refund."""
    
    # Verify purchase ownership
    purchase = await sales_transaction_crud.get_by_id(db, purchase_id)
    if not purchase or str(purchase.userId) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found or access denied"
        )
    
    # Get payment transaction
    payment_transaction = None
    if purchase.stripe_payment_intent_id:
        payment_transaction = await crud_payment_transactions.get_by_stripe_id(
            db, purchase.stripe_payment_intent_id
        )
    
    is_eligible = await _is_refund_eligible(purchase, payment_transaction)
    reason = "Eligible for refund" if is_eligible else "Not eligible for refund"
    
    if is_eligible:
        # Calculate refund window
        refund_deadline = purchase.purchaseDate + timedelta(days=30)
        days_remaining = (refund_deadline - datetime.utcnow()).days
        
        return {
            "eligible": True,
            "reason": reason,
            "refund_deadline": refund_deadline.isoformat(),
            "days_remaining": max(0, days_remaining),
            "max_refund_amount": float(purchase.total)
        }
    else:
        return {
            "eligible": False,
            "reason": reason,
            "refund_deadline": None,
            "days_remaining": 0,
            "max_refund_amount": 0.0
        }


# Helper functions
async def _can_download(purchase_details) -> bool:
    """Check if download is allowed for this purchase."""
    
    # Check maximum downloads
    max_downloads = purchase_details.max_downloads or 5
    if purchase_details.download_count >= max_downloads:
        return False
    
    # Check if download period has expired (default 30 days)
    download_period = timedelta(days=30)
    purchase_age = datetime.utcnow() - purchase_details.created_at
    
    if purchase_age > download_period:
        return False
    
    return True


async def _is_download_expired(purchase_details) -> bool:
    """Check if download period has expired."""
    download_period = timedelta(days=30)
    purchase_age = datetime.utcnow() - purchase_details.created_at
    return purchase_age > download_period


async def _is_support_eligible(purchase) -> bool:
    """Check if purchase is eligible for support."""
    
    # Support is available for 90 days after purchase
    support_period = timedelta(days=90)
    purchase_age = datetime.utcnow() - purchase.purchaseDate
    
    if purchase_age > support_period:
        return False
    
    # Only completed purchases are eligible
    if purchase.status != "completed":
        return False
    
    return True


async def _is_refund_eligible(purchase, payment_transaction) -> bool:
    """Check if purchase is eligible for refund."""
    
    # Only completed purchases can be refunded
    if purchase.status != "completed":
        return False
    
    # Check refund window (30 days)
    refund_window = timedelta(days=30)
    purchase_age = datetime.utcnow() - purchase.purchaseDate
    
    if purchase_age > refund_window:
        return False
    
    # Check if already refunded
    if payment_transaction and payment_transaction.refund_id:
        return False
    
    return True


async def _send_support_notification(ticket, user, purchase):
    """Send support ticket notification (background task)."""
    # This would integrate with your notification service
    # For now, we'll just log it
    print(f"Support ticket created: {ticket.id} for purchase {purchase.id} by user {user.username}")