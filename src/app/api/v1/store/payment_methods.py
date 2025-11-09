"""Payment methods and payout management endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.db.database import async_get_db
from src.app.core.security import get_current_user
from src.app.models.user import User
from src.app.schemas.payment_methods import (
    PaymentMethodCreate,
    PaymentMethodUpdate,
    PaymentMethodResponse,
    PayoutSettingsUpdate,
    PayoutSettingsResponse,
    PayoutHistoryResponse,
    EarningsSummary,
    PaymentMethodVerificationRequest,
    PaymentMethodVerificationResponse
)
from src.app.crud import crud_payment_method, crud_payout_settings

router = APIRouter(prefix="/commerce", tags=["Payment Methods"])

def extract_list(result):
    # tuple: (list, count)
    if isinstance(result, tuple):
        return result[0]

    # dict pagination shape: {"data": [...], "total_count": N}
    if isinstance(result, dict) and "data" in result:
        return result["data"]

    # otherwise return as-is (if it's already a list)
    return result

@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    include_unverified: bool = True,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all payment methods for the current user."""
    payment_methods = await crud_payment_method.get_user_payment_methods(
        db, current_user.id, include_unverified
    )
    return extract_list(payment_methods)


@router.post("/payment-methods", response_model=PaymentMethodResponse)
async def create_payment_method(
    payment_method: PaymentMethodCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new payment method."""
    
    # Check if user already has 5 payment methods (limit)
    existing_methods = await crud_payment_method.get_user_payment_methods(db, current_user.id)
    if len(existing_methods) >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of payment methods (5) reached"
        )
    
    # Create masked version of account info
    masked_info = crud_payment_method._create_masked_info(crud_payment_method, payment_method.account_info)
    
    new_payment_method = await crud_payment_method.create(
        db=db,
        user_id=current_user.id,
        method_type=payment_method.method_type,
        provider=payment_method.provider,
        account_info=payment_method.account_info,  # In production, encrypt this
        masked_info=masked_info,
        is_primary=payment_method.is_primary
    )
    
    return new_payment_method


@router.put("/payment-methods/{payment_method_id}", response_model=PaymentMethodResponse)
async def update_payment_method(
    payment_method_id: str,
    update_data: PaymentMethodUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a payment method."""
    
    # Verify ownership
    payment_method = await crud_payment_method.get_by_id(db, payment_method_id)
    if not payment_method or payment_method.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    updated_method = await crud_payment_method.update(
        db=db,
        payment_method_id=payment_method_id,
        provider=update_data.provider,
        account_info=update_data.account_info,
        is_primary=update_data.is_primary
    )
    
    if not updated_method:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update payment method"
        )
    
    return updated_method


@router.delete("/payment-methods/{payment_method_id}")
async def delete_payment_method(
    payment_method_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a payment method."""
    
    # Verify ownership
    payment_method = await crud_payment_method.get_by_id(db, payment_method_id)
    if not payment_method or payment_method.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    # Don't allow deletion of primary method if user has earnings
    if payment_method.is_primary:
        # In production, check if user has pending earnings
        # For now, just allow deletion
        pass
    
    success = await crud_payment_method.delete(db, payment_method_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete payment method"
        )
    
    return {"message": "Payment method deleted successfully"}


@router.post("/payment-methods/{payment_method_id}/verify", response_model=PaymentMethodVerificationResponse)
async def verify_payment_method(
    payment_method_id: str,
    verification_data: PaymentMethodVerificationRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit verification information for a payment method."""
    
    # Verify ownership
    payment_method = await crud_payment_method.get_by_id(db, payment_method_id)
    if not payment_method or payment_method.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    # In production, this would integrate with payment processor verification
    # For now, we'll simulate verification
    verification_result = await crud_payment_method.mark_as_verified(
        db=db,
        payment_method_id=payment_method_id,
        verification_data=verification_data.additional_info or {}
    )
    
    if not verification_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification failed"
        )
    
    return PaymentMethodVerificationResponse(
        payment_method_id=payment_method_id,
        verification_status="verified",
        verification_message="Payment method verified successfully",
        required_actions=[],
        estimated_verification_time=None
    )


@router.get("/payout-settings", response_model=PayoutSettingsResponse)
async def get_payout_settings(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get payout settings for the current user."""
    settings = await crud_payout_settings.get_by_user_id(db, current_user.id)
    
    if not settings:
        # Create default settings
        from decimal import Decimal
        settings = await crud_payout_settings.create_or_update(
            db=db,
            user_id=current_user.id,
            auto_payout_enabled=False,
            payout_threshold=Decimal("100.00"),
            payout_schedule="monthly",
            currency="USD"
        )
    
    return settings


@router.put("/payout-settings", response_model=PayoutSettingsResponse)
async def update_payout_settings(
    settings_update: PayoutSettingsUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Update payout settings for the current user."""
    
    # Verify primary payment method exists if auto payout is enabled
    if settings_update.auto_payout_enabled:
        primary_method = await crud_payment_method.get_primary_payment_method(db, current_user.id)
        if not primary_method or not primary_method.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auto payout requires a verified primary payment method"
            )
    
    settings = await crud_payout_settings.create_or_update(
        db=db,
        user_id=current_user.id,
        auto_payout_enabled=settings_update.auto_payout_enabled,
        payout_threshold=settings_update.payout_threshold,
        payout_schedule=settings_update.payout_schedule,
        primary_payment_method_id=settings_update.primary_payment_method_id,
        currency=settings_update.currency,
        tax_info=settings_update.tax_info
    )
    
    return settings


@router.get("/payout-history", response_model=PayoutHistoryResponse)
async def get_payout_history(
    limit: int = 50,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get payout history for the current user."""
    
    # In production, this would query actual payout records
    # For now, return mock data
    from decimal import Decimal
    from datetime import datetime, timedelta
    
    mock_payouts = [
        {
            "id": "payout_1",
            "user_id": current_user.id,
            "amount": Decimal("250.00"),
            "currency": "USD",
            "payment_method_id": "pm_123",
            "status": "completed",
            "transaction_id": "txn_abc123",
            "processed_at": datetime.utcnow() - timedelta(days=30),
            "created_at": datetime.utcnow() - timedelta(days=31)
        },
        {
            "id": "payout_2",
            "user_id": current_user.id,
            "amount": Decimal("180.00"),
            "currency": "USD",
            "payment_method_id": "pm_123",
            "status": "completed",
            "transaction_id": "txn_def456",
            "processed_at": datetime.utcnow() - timedelta(days=60),
            "created_at": datetime.utcnow() - timedelta(days=61)
        }
    ]
    
    return PayoutHistoryResponse(
        total_payouts=len(mock_payouts),
        total_amount=sum(p["amount"] for p in mock_payouts),
        payouts=mock_payouts,
        pending_amount=Decimal("125.50"),
        next_payout_date="2025-11-01"
    )


@router.get("/earnings-summary", response_model=EarningsSummary)
async def get_earnings_summary(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get earnings summary for the current user."""
    
    # In production, this would calculate from actual transaction data
    from decimal import Decimal
    from datetime import datetime, timedelta
    
    return EarningsSummary(
        total_earnings=Decimal("1250.75"),
        available_for_payout=Decimal("125.50"),
        pending_payout=Decimal("0.00"),
        total_paid_out=Decimal("1125.25"),
        current_month_earnings=Decimal("89.75"),
        last_payout_date=datetime.utcnow() - timedelta(days=30),
        next_payout_date="2025-11-01"
    )


@router.post("/request-payout")
async def request_manual_payout(
    amount: Optional[float] = None,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Request a manual payout."""
    
    # Verify user has a verified payment method
    primary_method = await crud_payment_method.get_primary_payment_method(db, current_user.id)
    if not primary_method or not primary_method.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A verified primary payment method is required for payouts"
        )
    
    # Get payout settings
    settings = await crud_payout_settings.get_by_user_id(db, current_user.id)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payout settings not configured"
        )
    
    # Validate payout amount (in production, check against available earnings)
    if amount and amount < settings.threshold_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum payout amount is ${settings.threshold_amount}"
        )
    
    # In production, create payout request and process it
    return {
        "message": "Payout request submitted successfully",
        "payout_id": "payout_new_123",
        "amount": amount or settings.threshold_amount,
        "estimated_processing_time": "2-3 business days",
        "payment_method": primary_method.display_name
    }