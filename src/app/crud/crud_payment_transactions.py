"""CRUD operations for payment transactions."""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta
import uuid

from ..models import PaymentTransaction
from ..schemas import PaymentTransactionCreate, PaymentTransactionUpdate


class CRUDPaymentTransactions:
    """CRUD operations for payment transactions."""
    
    async def get_by_stripe_id(
        self, db: AsyncSession, stripe_payment_intent_id: str
    ) -> Optional[PaymentTransaction]:
        """Get payment transaction by Stripe payment intent ID."""
        stmt = select(PaymentTransaction).where(
            PaymentTransaction.stripe_payment_intent_id == stripe_payment_intent_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id(
        self, db: AsyncSession, transaction_id: str
    ) -> Optional[PaymentTransaction]:
        """Get payment transaction by ID."""
        stmt = select(PaymentTransaction).where(PaymentTransaction.id == transaction_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_user_id(
        self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[PaymentTransaction]:
        """Get all payment transactions for a user."""
        stmt = (
            select(PaymentTransaction)
            .where(PaymentTransaction.user_id == user_id)
            .order_by(desc(PaymentTransaction.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def create(
        self, db: AsyncSession, obj_in: PaymentTransactionCreate
    ) -> PaymentTransaction:
        """Create a new payment transaction."""
        db_obj = PaymentTransaction(
            id=str(uuid.uuid4()),
            stripe_payment_intent_id=obj_in.stripe_payment_intent_id,
            stripe_customer_id=obj_in.stripe_customer_id,
            user_id=obj_in.user_id,
            amount=obj_in.amount,
            currency=obj_in.currency,
            status=obj_in.status,
            payment_method=obj_in.payment_method,
            metadata=obj_in.metadata or {}
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, db: AsyncSession, *, db_obj: PaymentTransaction, obj_in: PaymentTransactionUpdate
    ) -> PaymentTransaction:
        """Update a payment transaction."""
        update_data = obj_in.dict(exclude_unset=True)
        
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        
        db_obj.updated_at = datetime.utcnow()
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update_status(
        self, db: AsyncSession, *, stripe_payment_intent_id: str, status: str
    ) -> Optional[PaymentTransaction]:
        """Update payment transaction status."""
        transaction = await self.get_by_stripe_id(db, stripe_payment_intent_id)
        if not transaction:
            return None
        
        transaction.status = status
        transaction.updated_at = datetime.utcnow()
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
        return transaction
    
    async def mark_as_refunded(
        self,
        db: AsyncSession,
        *,
        stripe_payment_intent_id: str,
        refund_id: str,
        refund_amount: float,
        refund_reason: Optional[str] = None
    ) -> Optional[PaymentTransaction]:
        """Mark a payment transaction as refunded."""
        transaction = await self.get_by_stripe_id(db, stripe_payment_intent_id)
        if not transaction:
            return None
        
        transaction.refund_id = refund_id
        transaction.refund_amount = refund_amount
        transaction.refund_reason = refund_reason
        transaction.status = "refunded"
        transaction.updated_at = datetime.utcnow()
        
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
        return transaction
    
    async def get_recent_transactions(
        self, db: AsyncSession, hours: int = 24
    ) -> List[PaymentTransaction]:
        """Get recent transactions within the specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(PaymentTransaction)
            .where(PaymentTransaction.created_at >= cutoff_time)
            .order_by(desc(PaymentTransaction.created_at))
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_status(
        self, db: AsyncSession, status: str, skip: int = 0, limit: int = 100
    ) -> List[PaymentTransaction]:
        """Get payment transactions by status."""
        stmt = (
            select(PaymentTransaction)
            .where(PaymentTransaction.status == status)
            .order_by(desc(PaymentTransaction.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def delete(self, db: AsyncSession, *, transaction_id: str) -> bool:
        """Delete a payment transaction."""
        transaction = await self.get_by_id(db, transaction_id)
        if not transaction:
            return False
        
        await db.delete(transaction)
        await db.commit()
        return True


# Create instance
crud_payment_transactions = CRUDPaymentTransactions()