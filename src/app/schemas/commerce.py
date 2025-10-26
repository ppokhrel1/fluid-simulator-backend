"""Commerce system Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


# Design Asset Schemas
class DesignAssetBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    category: Optional[str] = None
    status: str = "draft"  # active|draft|sold|paused


class DesignAssetCreate(DesignAssetBase):
    seller_id: int
    original_model_id: Optional[int] = None


class DesignAssetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[str] = None
    status: Optional[str] = None


class DesignAssetUpdateInternal(DesignAssetUpdate):
    pass


class DesignAssetDelete(BaseModel):
    pass


class DesignAssetRead(DesignAssetBase):
    id: str
    sales: int = 0
    revenue: Decimal = Decimal("0.00")
    views: int = 0
    likes: int = 0
    seller_id: int
    original_model_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Sell Design Form Schema
class SellDesignForm(BaseModel):
    designName: str
    description: str
    price: str
    category: str  # aerospace|automotive|mechanical|architecture|industrial|other
    fileOrigin: str  # original|modified|commissioned
    licenseType: str  # commercial|personal|attribution|non-commercial
    originDeclaration: bool
    qualityAssurance: bool
    technicalSpecs: str
    tags: str
    instructions: str


# Cart Item Schemas
class CartItemBase(BaseModel):
    design_id: str
    name: str
    price: Decimal
    original_price: Optional[Decimal] = None
    size: str
    color: str
    icon: str
    quantity: int = 1


class CartItemCreate(CartItemBase):
    user_id: int


class CartItemUpdate(BaseModel):
    quantity: Optional[int] = None
    size: Optional[str] = None
    color: Optional[str] = None


class CartItemUpdateInternal(CartItemUpdate):
    pass


class CartItemDelete(BaseModel):
    pass


class CartItemRead(CartItemBase):
    id: str
    user_id: int
    added_at: datetime
    
    class Config:
        from_attributes = True


# Sales Transaction Schemas
class SalesTransactionBase(BaseModel):
    design_id: str
    design_name: str
    buyer_id: int
    buyer_email: str
    price: Decimal
    status: str = "completed"  # completed|pending|refunded
    transaction_id: Optional[str] = None
    commission_rate: Decimal = Decimal("0.10")
    seller_earnings: Decimal


class SalesTransactionCreate(SalesTransactionBase):
    pass


class SalesTransactionUpdate(BaseModel):
    status: Optional[str] = None


class SalesTransactionUpdateInternal(SalesTransactionUpdate):
    pass


class SalesTransactionDelete(BaseModel):
    pass


class SalesTransactionRead(SalesTransactionBase):
    id: str
    date: datetime
    
    class Config:
        from_attributes = True


# Payout Schemas
class PayoutBase(BaseModel):
    amount: Decimal
    method: str  # paypal|stripe|bank_transfer
    fees: Decimal = Decimal("0.00")
    net_amount: Decimal
    payout_account: Optional[str] = None


class PayoutCreate(PayoutBase):
    seller_id: int


class PayoutUpdate(BaseModel):
    status: Optional[str] = None  # pending|processing|completed|failed
    processed_date: Optional[datetime] = None


class PayoutUpdateInternal(PayoutUpdate):
    pass


class PayoutDelete(BaseModel):
    pass


class PayoutRead(PayoutBase):
    id: str
    seller_id: int
    status: str
    request_date: datetime
    processed_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True