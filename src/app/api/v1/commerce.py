"""Commerce endpoints for design marketplace."""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.security import get_current_user
from ...crud.crud_commerce import design_asset_crud, cart_item_crud, sales_transaction_crud, payout_crud
from ...models.user import User
from ...schemas.commerce import (
    DesignAssetCreate, DesignAssetUpdate, DesignAssetRead,
    CartItemCreate, CartItemUpdate, CartItemRead,
    SalesTransactionCreate, SalesTransactionRead,
    PayoutCreate, PayoutUpdate, PayoutRead,
    SellDesignForm
)

router = APIRouter()


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
    return designs


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
        seller_id=current_user.id,  # Get from authenticated user
        original_model_id=None  # Can be enhanced later
    )
    
    design = await design_asset_crud.create(db, obj_in=design_data.model_dump())
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
    return cart_items


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
    
    return transactions


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
    return sales


# Payout Endpoints
@router.get("/payouts", response_model=List[PayoutRead])
async def get_payouts(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's payout history."""
    payouts = await payout_crud.get_seller_payouts(db, current_user.id)
    return payouts


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
