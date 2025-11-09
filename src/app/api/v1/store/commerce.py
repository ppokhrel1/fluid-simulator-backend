"""Commerce endpoints for design marketplace."""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.db.database import async_get_db
from src.app.core.security import get_current_user
from src.app.crud.crud_commerce import design_asset_crud, cart_item_crud, sales_transaction_crud, payout_crud
from src.app.models.user import User
from src.app.schemas.commerce import (
    DesignAssetCreate, DesignAssetUpdate, DesignAssetRead,
    CartItemCreate, CartItemUpdate, CartItemRead,
    SalesTransactionCreate, SalesTransactionRead,
    PayoutCreate, PayoutUpdate, PayoutRead,
    SellDesignForm, DesignAssetPaginatedRead
)
from src.app.schemas.sales_management import (
    DesignUpdateRequest, DesignUpdateResponse,
    PromotionRequest, PromotionResponse,
    DesignDuplicateRequest, DesignDuplicateResponse,
    DesignStatusUpdateRequest, DesignStatusUpdateResponse,
    EnhancedDesignResponse, 
)
from src.app.schemas.analytics import DesignAnalyticsResponse
from src.app.crud import crud_design_analytics, crud_promotion_campaign

router = APIRouter()

def extract_list(result):
    # tuple: (list, count)
    if isinstance(result, tuple):
        return result[0]

    # dict pagination shape: {"data": [...], "total_count": N}
    if isinstance(result, dict) and "data" in result:
        return result["data"]

    # otherwise return as-is (if it's already a list)
    return result

# Design Assets Endpoints
@router.get("/designs", response_model=List[DesignAssetRead])
async def get_designs(
    category: str = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(async_get_db)
):
    """Get all design assets or filter by category."""
    if category:
        designs = await design_asset_crud.get_by_category(db, category, limit, offset)
    else:
        designs = await design_asset_crud.get_multi(db, limit=limit, offset=offset)
    return extract_list(designs)


@router.post("/designs", response_model=DesignAssetRead)
async def create_design(
    design_data: DesignAssetCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new design asset for sale."""
    design_data_dict = design_data.model_dump()
    design_data_dict["seller_id"] = current_user.id
    design = await design_asset_crud.create(db, obj_in=design_data_dict)
    return design


@router.post("/designs/sell", response_model=DesignAssetRead)
async def sell_design(
    form_data: SellDesignForm,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new design asset from frontend sell form."""
    from decimal import Decimal
    
    # Convert frontend form data to backend schema
    design_data = DesignAssetCreate(
        name=form_data.designName,  # Convert designName -> name
        description=form_data.description,
        price=Decimal(form_data.price),  # Convert string to Decimal
        category=form_data.category,
        status="active",  # Set as active since it's being sold
        seller_id=current_user['id'],  # Get from authenticated user
        original_model_id=None  # Can be enhanced later
    )
    
    design = await design_asset_crud.create(db, object=design_data)
    return design


@router.get("/designs/{design_id}", response_model=DesignAssetRead)
async def get_design(
    design_id: str,
    db: AsyncSession = Depends(async_get_db)
):
    """Get a specific design asset and increment view count."""
    design = await design_asset_crud.get(db, id=design_id)
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found"
        )
    
    # Increment view count
    await design_asset_crud.increment_views(db, design_id)
    
    return design


@router.put("/designs/{design_id}", response_model=DesignAssetRead)
async def update_design(
    design_id: str,
    design_data: DesignAssetUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a design asset (only by seller)."""
    design = await design_asset_crud.get(db, id=design_id)
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found"
        )
    
    if design.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the seller can update this design"
        )
    
    updated_design = await design_asset_crud.update(db, db_obj=design, obj_in=design_data)
    return updated_design


@router.post("/designs/{design_id}/like")
async def like_design(
    design_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Like a design asset."""
    design = await design_asset_crud.get(db, id=design_id)
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found"
        )
    
    await design_asset_crud.increment_likes(db, design_id)
    return {"message": "Design liked successfully"}


# Cart Endpoints
@router.get("/cart", response_model=List[CartItemRead])
async def get_cart(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's cart items."""
    cart_items = await cart_item_crud.get_user_cart(db, current_user.id)
    return extract_list(cart_items)


@router.post("/cart", response_model=CartItemRead)
async def add_to_cart(
    cart_item: CartItemCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Add item to cart."""
    cart_item_dict = cart_item.model_dump()
    cart_item_dict["user_id"] = current_user.id
    new_cart_item = await cart_item_crud.create(db, obj_in=cart_item_dict)
    return new_cart_item


@router.put("/cart/{cart_item_id}", response_model=CartItemRead)
async def update_cart_item(
    cart_item_id: str,
    cart_item_update: CartItemUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Update cart item quantity."""
    cart_item = await cart_item_crud.get(db, id=cart_item_id)
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    if cart_item.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own cart items"
        )
    
    updated_item = await cart_item_crud.update(db, db_obj=cart_item, obj_in=cart_item_update)
    return updated_item


@router.delete("/cart/{cart_item_id}")
async def remove_from_cart(
    cart_item_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove item from cart."""
    cart_item = await cart_item_crud.get(db, id=cart_item_id)
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    if cart_item.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only remove your own cart items"
        )
    
    await cart_item_crud.remove(db, id=cart_item_id)
    return {"message": "Item removed from cart"}


@router.delete("/cart")
async def clear_cart(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear all items from cart."""
    await cart_item_crud.clear_user_cart(db, current_user.id)
    return {"message": "Cart cleared successfully"}


# Checkout Endpoint
@router.post("/checkout", response_model=List[SalesTransactionRead])
async def checkout(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Process checkout for all cart items."""
    cart_items = await cart_item_crud.get_user_cart(db, current_user.id)
    
    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty"
        )
    
    transactions = []
    for item in cart_items:
        # Get design asset to calculate total
        design = await design_asset_crud.get(db, id=item.design_id)
        if not design:
            continue
        
        transaction_data = {
            "buyer_id": current_user.id,
            "design_id": item.design_id,
            "quantity": item.quantity,
            "unit_price": design.price,
            "total_amount": design.price * item.quantity,
            "status": "completed"
        }
        
        transaction = await sales_transaction_crud.create(db, obj_in=transaction_data)
        transactions.append(transaction)
    
    # Clear cart after successful checkout
    await cart_item_crud.clear_user_cart(db, current_user.id)
    
    return extract_list(transactions)


# Sales Endpoints
@router.get("/sales/purchases", response_model=List[SalesTransactionRead])
async def get_user_purchases(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's purchase history."""
    purchases = await sales_transaction_crud.get_user_purchases(db, current_user.id)
    return purchases


@router.get("/sales/seller", response_model=List[SalesTransactionRead])
async def get_seller_sales(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's sales history."""
    sales = await sales_transaction_crud.get_seller_sales(db, current_user.id)
    return extract_list(sales)


# Payout Endpoints
@router.get("/payouts", response_model=List[PayoutRead])
async def get_payouts(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's payout history."""
    payouts = await payout_crud.get_seller_payouts(db, current_user.id)
    return extract_list(payouts)


@router.post("/payouts", response_model=PayoutRead)
async def request_payout(
    payout_request: PayoutCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Request a payout."""
    payout_data = payout_request.model_dump()
    payout_data["seller_id"] = current_user.id
    payout_data["status"] = "pending"
    
    payout = await payout_crud.create(db, obj_in=payout_data)
    return payout


# NEW DASHBOARD SALES MANAGEMENT ENDPOINTS

@router.put("/designs/{design_id}/manage", response_model=DesignUpdateResponse)
async def update_design_advanced(
    design_id: str,
    update_data: DesignUpdateRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Advanced design update with Dashboard features."""
    design = await design_asset_crud.get(db, id=design_id)
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found"
        )
    
    if design.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the seller can update this design"
        )
    
    # Convert optional fields to update dict
    update_dict = {}
    if update_data.designName is not None:
        update_dict["name"] = update_data.designName
    if update_data.description is not None:
        update_dict["description"] = update_data.description
    if update_data.price is not None:
        update_dict["price"] = update_data.price
    if update_data.category is not None:
        update_dict["category"] = update_data.category
    if update_data.status is not None:
        update_dict["status"] = update_data.status
    
    # Update design
    from datetime import datetime
    update_dict["lastModified"] = datetime.utcnow()
    
    updated_design = await design_asset_crud.update(db, db_obj=design, obj_in=update_dict)
    
    return DesignUpdateResponse(
        id=updated_design.id,
        designName=updated_design.name,
        description=updated_design.description,
        price=updated_design.price,
        category=updated_design.category,
        status=updated_design.status,
        lastModified=updated_design.lastModified or datetime.utcnow()
    )


@router.post("/designs/{design_id}/promote", response_model=PromotionResponse)
async def promote_design(
    design_id: str,
    promotion_data: PromotionRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a promotion campaign for a design."""
    design = await design_asset_crud.get(db, id=design_id)
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found"
        )
    
    if design.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the seller can promote this design"
        )
    
    # Create promotion campaign
    campaign = await crud_promotion_campaign.create(
        db=db,
        design_id=design_id,
        user_id=current_user.id,
        campaign_name=f"{design.name} - {promotion_data.promotion_type.title()} Campaign",
        campaign_type=promotion_data.promotion_type,
        duration_days=promotion_data.duration_days,
        budget=promotion_data.budget
    )
    
    return PromotionResponse(
        campaign_id=campaign.id,
        design_id=design_id,
        campaign_type=campaign.campaign_type,
        status=campaign.status,
        duration_days=campaign.duration_days,
        budget=campaign.budget,
        created_at=campaign.created_at,
        expires_at=campaign.expires_at,
        estimated_reach=1000  # Mock value
    )


@router.get("/designs/{design_id}/analytics", response_model=DesignAnalyticsResponse)
async def get_design_analytics(
    design_id: str,
    days: int = 30,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analytics data for a design."""
    design = await design_asset_crud.get(db, id=design_id)
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found"
        )
    
    if design.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the seller can view analytics for this design"
        )
    
    # Get aggregated analytics
    stats = await crud_design_analytics.get_aggregated_design_stats(db, design_id, days)
    
    return DesignAnalyticsResponse(
        design_id=design_id,
        views=stats.get('total_views', 0),
        unique_viewers=stats.get('total_unique_viewers', 0),
        likes=stats.get('total_likes', 0),
        downloads=stats.get('total_downloads', 0),
        revenue=stats.get('total_revenue', 0),
        conversion_rate=stats.get('conversion_rate', 0.0),
        average_rating=4.5,  # Mock value
        total_reviews=10,    # Mock value
        traffic_sources={
            "direct": 40,
            "search": 35,
            "social": 15,
            "referral": 10
        },
        performance_trend=[
            {"date": "2025-10-01", "views": 50, "sales": 2},
            {"date": "2025-10-02", "views": 45, "sales": 1},
            {"date": "2025-10-03", "views": 60, "sales": 3}
        ]
    )


@router.post("/designs/{design_id}/duplicate", response_model=DesignDuplicateResponse)
async def duplicate_design(
    design_id: str,
    duplicate_data: DesignDuplicateRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Duplicate an existing design."""
    original_design = await design_asset_crud.get(db, id=design_id)
    if not original_design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found"
        )
    
    if original_design.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the seller can duplicate this design"
        )
    
    # Create duplicate design
    from datetime import datetime
    duplicate_data_dict = {
        "name": duplicate_data.new_name,
        "description": original_design.description if duplicate_data.copy_description else "",
        "price": original_design.price if duplicate_data.copy_price else 0,
        "category": original_design.category,
        "status": duplicate_data.status,
        "seller_id": current_user.id,
        "original_model_id": original_design.original_model_id,
        "uploadDate": datetime.utcnow(),
        "lastModified": datetime.utcnow()
    }
    
    new_design = await design_asset_crud.create(db, obj_in=duplicate_data_dict)
    
    return DesignDuplicateResponse(
        original_id=design_id,
        new_id=new_design.id,
        new_name=new_design.name,
        status=new_design.status,
        created_at=new_design.uploadDate
    )


@router.put("/designs/{design_id}/status", response_model=DesignStatusUpdateResponse)
async def update_design_status(
    design_id: str,
    status_data: DesignStatusUpdateRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Update design status (active, draft, paused, etc.)."""
    design = await design_asset_crud.get(db, id=design_id)
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found"
        )
    
    if design.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the seller can update this design status"
        )
    
    old_status = design.status
    from datetime import datetime
    updated_design = await design_asset_crud.update(
        db, 
        db_obj=design, 
        obj_in={"status": status_data.status, "lastModified": datetime.utcnow()}
    )
    
    return DesignStatusUpdateResponse(
        id=design_id,
        old_status=old_status,
        new_status=updated_design.status,
        updated_at=updated_design.lastModified or datetime.utcnow()
    )
