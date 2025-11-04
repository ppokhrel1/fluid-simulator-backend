"""CRUD operations for payment methods and payout settings."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from datetime import datetime
from decimal import Decimal
import uuid

from src.app.models.payment_methods import PaymentMethod, PayoutSettings


class CRUDPaymentMethod:
    """CRUD operations for payment methods."""
    
    async def create(
        self,
        db: AsyncSession,
        user_id: int,
        method_type: str,
        provider: str,
        account_info: str,
        masked_info: str = None,
        is_primary: bool = False
    ) -> PaymentMethod:
        """Create a new payment method."""
        # If this is set as primary, unset others
        if is_primary:
            await self._unset_primary_methods(db, user_id)
        
        payment_method = PaymentMethod(
            id=str(uuid.uuid4()),
            user_id=user_id,
            method_type=method_type,
            provider=provider,
            account_info=account_info,  # Should be encrypted in production
            masked_info=masked_info or self._create_masked_info(account_info),
            is_primary=is_primary
        )
        
        db.add(payment_method)
        await db.commit()
        await db.refresh(payment_method)
        return payment_method
    
    async def get_by_id(self, db: AsyncSession, payment_method_id: str) -> Optional[PaymentMethod]:
        """Get payment method by ID."""
        result = await db.execute(
            select(PaymentMethod).where(PaymentMethod.id == payment_method_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_payment_methods(
        self, 
        db: AsyncSession, 
        user_id: int,
        include_unverified: bool = True
    ) -> List[PaymentMethod]:
        """Get all payment methods for a user."""
        query = select(PaymentMethod).where(PaymentMethod.user_id == user_id)
        
        if not include_unverified:
            query = query.where(PaymentMethod.is_verified == True)
        
        query = query.order_by(PaymentMethod.is_primary.desc(), PaymentMethod.created_at.desc())
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_primary_payment_method(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> Optional[PaymentMethod]:
        """Get user's primary payment method."""
        result = await db.execute(
            select(PaymentMethod).where(
                and_(
                    PaymentMethod.user_id == user_id,
                    PaymentMethod.is_primary == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update(
        self,
        db: AsyncSession,
        payment_method_id: str,
        provider: str = None,
        account_info: str = None,
        is_primary: bool = None
    ) -> Optional[PaymentMethod]:
        """Update payment method."""
        payment_method = await self.get_by_id(db, payment_method_id)
        if not payment_method:
            return None
        
        if provider is not None:
            payment_method.provider = provider
        
        if account_info is not None:
            payment_method.account_info = account_info
            payment_method.masked_info = self._create_masked_info(account_info)
        
        if is_primary is not None:
            if is_primary:
                await self._unset_primary_methods(db, payment_method.user_id)
            payment_method.is_primary = is_primary
        
        await db.commit()
        await db.refresh(payment_method)
        return payment_method
    
    async def delete(self, db: AsyncSession, payment_method_id: str) -> bool:
        """Delete payment method."""
        payment_method = await self.get_by_id(db, payment_method_id)
        if not payment_method:
            return False
        
        await db.delete(payment_method)
        await db.commit()
        return True
    
    async def mark_as_verified(
        self, 
        db: AsyncSession, 
        payment_method_id: str,
        verification_data: Dict[str, Any] = None
    ) -> Optional[PaymentMethod]:
        """Mark payment method as verified."""
        payment_method = await self.get_by_id(db, payment_method_id)
        if not payment_method:
            return None
        
        payment_method.is_verified = True
        if verification_data:
            import json
            payment_method.verification_data = json.dumps(verification_data)
        
        await db.commit()
        await db.refresh(payment_method)
        return payment_method
    
    async def record_usage(self, db: AsyncSession, payment_method_id: str) -> bool:
        """Record usage of payment method."""
        payment_method = await self.get_by_id(db, payment_method_id)
        if not payment_method:
            return False
        
        payment_method.last_used = datetime.utcnow()
        await db.commit()
        return True
    
    def _create_masked_info(self, account_info: str) -> str:
        """Create masked version of account info for display."""
        if len(account_info) <= 4:
            return "*" * len(account_info)
        return "*" * (len(account_info) - 4) + account_info[-4:]
    
    async def _unset_primary_methods(self, db: AsyncSession, user_id: int):
        """Unset all primary methods for a user."""
        await db.execute(
            update(PaymentMethod)
            .where(PaymentMethod.user_id == user_id)
            .values(is_primary=False)
        )


class CRUDPayoutSettings:
    """CRUD operations for payout settings."""
    
    async def create_or_update(
        self,
        db: AsyncSession,
        user_id: int,
        auto_payout_enabled: bool = False,
        payout_threshold: Decimal = Decimal("100.00"),
        payout_schedule: str = "monthly",
        primary_payment_method_id: str = None,
        currency: str = "USD",
        tax_info: Dict[str, Any] = None
    ) -> PayoutSettings:
        """Create or update payout settings for a user."""
        # Try to get existing settings
        result = await db.execute(
            select(PayoutSettings).where(PayoutSettings.user_id == user_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing settings
            existing.auto_payout_enabled = auto_payout_enabled
            existing.payout_threshold = str(payout_threshold)
            existing.payout_schedule = payout_schedule
            existing.primary_payment_method_id = primary_payment_method_id
            existing.currency = currency
            if tax_info:
                import json
                existing.tax_info = json.dumps(tax_info)
            existing.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            # Create new settings
            import json
            settings = PayoutSettings(
                user_id=user_id,
                auto_payout_enabled=auto_payout_enabled,
                payout_threshold=str(payout_threshold),
                payout_schedule=payout_schedule,
                primary_payment_method_id=primary_payment_method_id,
                currency=currency,
                tax_info=json.dumps(tax_info or {})
            )
            
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
            return settings
    
    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> Optional[PayoutSettings]:
        """Get payout settings for a user."""
        result = await db.execute(
            select(PayoutSettings).where(PayoutSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_auto_payout_users(
        self, 
        db: AsyncSession,
        threshold_met: Decimal = None
    ) -> List[PayoutSettings]:
        """Get users eligible for auto payout."""
        query = select(PayoutSettings).where(PayoutSettings.auto_payout_enabled == True)
        
        # In a real implementation, you'd join with earnings data to check threshold
        # For now, just return all auto-payout enabled users
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update_payment_method(
        self,
        db: AsyncSession,
        user_id: int,
        payment_method_id: str
    ) -> Optional[PayoutSettings]:
        """Update primary payment method for user."""
        settings = await self.get_by_user_id(db, user_id)
        if not settings:
            return None
        
        settings.primary_payment_method_id = payment_method_id
        settings.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(settings)
        return settings


# Create instances
crud_payment_method = CRUDPaymentMethod()
crud_payout_settings = CRUDPayoutSettings()