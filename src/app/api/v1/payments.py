"""Payment management endpoints with Stripe integration."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from ...schemas.commerce import SalesTransactionCreate
from ...schemas.payment_transaction import PaymentTransactionCreate
from datetime import datetime, timedelta
import stripe 
import os
import json
from decimal import Decimal


from ...core.db.database import async_get_db
from ...core.security import get_current_user
from ...core.config import AppSettings
from ...models.user import User
from ...schemas.purchase_management import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentConfirmationRequest,
    PaymentConfirmationResponse,
    RefundRequest,
    RefundResponse,
    PaymentMethodResponse,
    SubscriptionPlanResponse,
    StripeWebhookResponse
)
from ...crud.crud_payment_transactions import crud_payment_transactions
from ...crud.crud_commerce import sales_transaction_crud


router = APIRouter(prefix="/payments", tags=["Payment Management"])

# Initialize Stripe with settings
settings = AppSettings()
stripe.api_key = settings.STRIPE_CLIENT_SECRET or settings.STRIPE_API_KEY


@router.post("/create-payment-link")
async def create_payment_link(item_data: dict):
    """Create a simple Stripe payment link (product+price+link)."""
    try:
        product = stripe.Product.create(
            name=item_data["name"],
            description=item_data.get("description", ""),
        )

        price = stripe.Price.create(
            product=product["id"],
            unit_amount=int(float(item_data["price"]) * 100),
            currency=item_data.get("currency", "usd"),
        )

        link = stripe.PaymentLink.create(
            line_items=[{"price": price["id"], "quantity": 1}],
            after_completion={"type": "redirect", "redirect": {"url": item_data.get("return_url", "/")}},
            metadata=item_data.get("metadata", {}),
        )

        return {"url": link.url, "payment_link_id": link["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-payment-intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    payment_data: PaymentIntentRequest,
    request: Request,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a Stripe Payment Intent for a purchase."""
    try:
        # Convert Decimal -> cents
        amount_cents = int(Decimal(payment_data.amount) * 100)

        # 🛑 FIX: Skip customer creation and set ID to None/null
        stripe_customer_id = None 

        metadata = payment_data.metadata or {}
        metadata.update({
            "user_id": str(current_user["id"]),
            "username": current_user["username"],
            "items_count": str(len(payment_data.items or [])),
            "purchase_type": payment_data.purchase_type
        })

        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=payment_data.currency.lower(),
            automatic_payment_methods={"enabled": True},
            # 🛑 FIX: Removed 'customer=stripe_customer_id' to skip required customer object
            metadata=metadata,
            receipt_email=metadata.get("email") or getattr(current_user, "email", None),
            description=f"Purchase for {metadata.get('items_count', '0')} items"
        )

        # Persist a payment transaction record (stripe_customer_id is None)
        pt_create = PaymentTransactionCreate(
            stripe_payment_intent_id=intent["id"],
            stripe_customer_id=stripe_customer_id, # Value is None
            user_id=current_user["id"],
            amount=Decimal(payment_data.amount),
            currency=payment_data.currency,
            status="pending",
            payment_method=None,
            metadata=metadata
        )

        try:
            # Assumes crud_payment_transactions.create handles obj_in properly
            await crud_payment_transactions.create(db=db, obj_in=pt_create)
        except Exception:
            # Non-fatal if DB write fails - log and continue
            pass

        return PaymentIntentResponse(
            payment_intent_id=intent["id"],
            client_secret=intent.client_secret,
            amount=Decimal(intent.amount) / Decimal(100),
            currency=intent.currency,
            status=intent.status,
            created=intent.created,
            payment_method_types=intent.payment_method_types,
            next_action=intent.next_action if hasattr(intent, "next_action") else None
        )
    except stripe.error.StripeError as se:
        raise HTTPException(status_code=502, detail=str(se))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/confirm-payment", response_model=PaymentConfirmationResponse)
async def confirm_payment(
    confirmation_data: PaymentConfirmationRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm and finalize a Stripe payment."""
    try:
        # 🛑 CRITICAL FIX: Retrieve the Intent instead of trying to Confirm it again.
        intent = stripe.PaymentIntent.retrieve(
            confirmation_data.payment_intent_id
        )

        # Update transaction status in DB
        await crud_payment_transactions.update_status(db=db, stripe_payment_intent_id=intent["id"], status=intent.status)

        print("Payment Intent retrieved:", intent)
        sales_id = None
        if intent.status == "succeeded":
            
            # --- START FIX ---
            
            # 1. Get the primary item ID and name
            first_item = confirmation_data.items[0] if confirmation_data.items else {}
            item_design_id = first_item.get("id") or first_item.get("design_id", "00000000-0000-0000-0000-000000000000")
            item_design_name = first_item.get("name", f"Order {intent['id']}")
            
            try:
                # 2. Instantiate Sales Transaction Pydantic model
                sales_input_model = SalesTransactionCreate( 
                    user_id=current_user["id"],
                    items=confirmation_data.items,
                    total=Decimal(intent.amount) / Decimal(100),
                    stripe_payment_intent_id=intent["id"],
                    status="completed",
                    
                    # Map the actual Design ID from the cart item
                    design_id=item_design_id, 
                    design_name=item_design_name, 
                    buyer_id=current_user["id"],
                    buyer_email=current_user["email"], # Assuming current_user has email
                    price=Decimal(intent.amount) / Decimal(100), 
                    seller_earnings=Decimal(intent.amount) / Decimal(100) * Decimal("0.9"), 
                )
                
                # 3. Call CRUD to create the record
                if hasattr(sales_transaction_crud, "create"):
                    created = await sales_transaction_crud.create(db=db, object=sales_input_model) 
                    # Use getattr and then convert to string
                    raw_sales_id = getattr(created, "id", None)
                    
                    # 🛑 CRITICAL FIX: Convert the UUID object to a string before assigning to sales_id
                    sales_id = str(raw_sales_id) if raw_sales_id is not None else None
            
            except Exception as e:        
                # Log error but continue (Stripe transaction is already succeeded)
                print(f"Error creating sales transaction: {str(e)}")
                sales_id = None
            # --- END FIX ---
            
        return PaymentConfirmationResponse(
            payment_intent_id=intent["id"],
            status=intent.status,
            # sales_id is already a string (or None) due to the fix above
            sales_transaction_id=sales_id,
            amount=Decimal(intent.amount) / Decimal(100),
            currency=intent.currency,
            receipt_url=getattr(intent, "charges", {}).get("data", [{}])[0].get("receipt_url") if getattr(intent, "charges", None) else None,
            confirmed_at=datetime.utcnow().isoformat()
        )
    except Exception as e:
        # Catch unexpected errors during retrieval or DB update
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/refund", response_model=RefundResponse)
async def create_refund(
    refund_data: RefundRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a refund for a payment."""
    try:
        # Retrieve payment transaction
        payment_tx = await crud_payment_transactions.get_by_stripe_id(db, refund_data.payment_intent_id)
        if not payment_tx:
            raise HTTPException(status_code=404, detail="Payment transaction not found")

        # Validate eligibility
        if not await _is_refund_eligible(payment_tx, refund_data):
            raise HTTPException(status_code=400, detail="Refund not eligible")

        # Create refund in Stripe. If amount is omitted, refund full charge.
        # Need a charge id - try to find latest charge on the payment intent
        pi = stripe.PaymentIntent.retrieve(refund_data.payment_intent_id, expand=["charges.data"])
        charge_id = None
        if getattr(pi, "charges", None) and pi.charges.data:
            charge_id = pi.charges.data[0]["id"]

        refund_kwargs = {"payment_intent": refund_data.payment_intent_id}
        if refund_data.amount:
            refund_kwargs["amount"] = int(Decimal(refund_data.amount) * 100)
        if refund_data.reason:
            refund_kwargs["reason"] = refund_data.reason

        refund = stripe.Refund.create(**refund_kwargs)

        # Mark refunded in DB
        await crud_payment_transactions.mark_as_refunded(
            db=db,
            stripe_payment_intent_id=refund_data.payment_intent_id,
            refund_id=refund["id"],
            refund_amount=float((refund.amount or 0) / 100),
            refund_reason=refund.reason if hasattr(refund, "reason") else None
        )

        return RefundResponse(
            refund_id=refund["id"],
            payment_intent_id=refund_data.payment_intent_id,
            amount=Decimal(refund.amount) / Decimal(100),
            currency=getattr(refund, "currency", "usd"),
            status=refund.status,
            reason=getattr(refund, "reason", None),
            created=getattr(refund, "created", int(datetime.utcnow().timestamp()))
        )
    except stripe.error.StripeError as se:
        raise HTTPException(status_code=502, detail=str(se))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's saved payment methods from Stripe."""
    # This endpoint is stubbed as we are not using Stripe Customer objects.
    return []


@router.get("/subscription-plans", response_model=List[SubscriptionPlanResponse])
async def get_subscription_plans():
    """Get available subscription plans from Stripe."""
    try:
        prices = stripe.Price.list(active=True, limit=100, expand=["data.product"])
        out = []
        for p in getattr(prices, "data", []):
            product = getattr(p, "product", None) or {}
            out.append(SubscriptionPlanResponse(
                plan_id=p["id"],
                product_id=getattr(product, "id", getattr(product, "object_id", "")),
                name=getattr(product, "name", str(getattr(product, "id", ""))),
                description=getattr(product, "description", None),
                amount=Decimal(p.unit_amount or 0) / Decimal(100),
                currency=p.currency,
                interval=getattr(p.recurring, "interval", "one_time") if getattr(p, "recurring", None) else "one_time",
                interval_count=getattr(p.recurring, "interval_count", 1) if getattr(p, "recurring", None) else 1,
                features=[]
            ))
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(async_get_db)
):
    """Handle Stripe webhook events."""
    
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Process webhook events in background
    processed_events = []
    
    if event['type'] == 'payment_intent.succeeded':
        background_tasks.add_task(_handle_payment_succeeded, event, db)
        processed_events.append('payment_intent.succeeded')
    
    elif event['type'] == 'payment_intent.payment_failed':
        background_tasks.add_task(_handle_payment_failed, event, db)
        processed_events.append('payment_intent.payment_failed')
    
    elif event['type'] == 'charge.refunded':
        background_tasks.add_task(_handle_refund_processed, event, db)
        processed_events.append('charge.refunded')
    
    elif event['type'] == 'payment_intent.canceled':
        background_tasks.add_task(_handle_payment_canceled, event, db)
        processed_events.append('payment_intent.canceled')
    
    return {"status": "success", "processed_events": processed_events}


@router.get("/{payment_intent_id}/status")
async def get_payment_status(
    payment_intent_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the status of a payment intent."""
    
    try:
        # Retrieve payment intent from Stripe
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        # Verify ownership
        payment_transaction = await crud_payment_transactions.get_by_stripe_id(db, payment_intent_id)
        if not payment_transaction or payment_transaction.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this payment"
            )
        
        return {
            "payment_intent_id": payment_intent["id"],
            "status": payment_intent.status,
            "amount": payment_intent.amount / 100,
            "currency": payment_intent.currency,
            "created": payment_intent.created,
            "last_payment_error": getattr(payment_intent, 'last_payment_error', None)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error retrieving payment status: {str(e)}"
        )


# Helper functions
# 🛑 Removed _get_or_create_stripe_customer function.


async def _is_refund_eligible(payment_transaction, refund_data: RefundRequest) -> bool:
    """Check if a refund is eligible for the given transaction."""
    
    # Check if payment was successful
    if payment_transaction.status != "succeeded":
        return False
    
    # Check if refund is within time limit (e.g., 30 days)
    refund_window = timedelta(days=30)
    transaction_age = datetime.utcnow() - payment_transaction.created_at
    
    if transaction_age > refund_window:
        return False
    
    # Check if refund amount is valid
    if refund_data.amount and float(refund_data.amount) > payment_transaction.amount:
        return False
    
    # Additional business logic checks can be added here
    
    return True


async def _handle_payment_succeeded(event: Dict[str, Any], db: AsyncSession):
    """Handle successful payment webhook."""
    
    payment_intent = event['data']['object']
    
    # Update payment transaction status
    await crud_payment_transactions.update_status(
        db=db,
        stripe_payment_intent_id=payment_intent['id'],
        status="succeeded",
        metadata={"webhook_processed_at": datetime.utcnow().isoformat()}
    )


async def _handle_payment_failed(event: Dict[str, Any], db: AsyncSession):
    """Handle failed payment webhook."""
    
    payment_intent = event['data']['object']
    
    # Update payment transaction status
    await crud_payment_transactions.update_status(
        db=db,
        stripe_payment_intent_id=payment_intent['id'],
        status="failed",
        metadata={
            "webhook_processed_at": datetime.utcnow().isoformat(),
            "failure_message": payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')
        }
    )


async def _handle_refund_processed(event: Dict[str, Any], db: AsyncSession):
    """Handle refund processed webhook."""
    
    charge = event['data']['object']
    payment_intent_id = charge.get('payment_intent')
    
    if payment_intent_id:
        # Update payment transaction with refund info
        await crud_payment_transactions.update_refund_status(
            db=db,
            stripe_payment_intent_id=payment_intent_id,
            refund_status="processed",
            metadata={"webhook_processed_at": datetime.utcnow().isoformat()}
        )


async def _handle_payment_canceled(event: Dict[str, Any], db: AsyncSession):
    """Handle canceled payment webhook."""
    
    payment_intent = event['data']['object']
    
    # Update payment transaction status
    await crud_payment_transactions.update_status(
        db=db,
        stripe_payment_intent_id=payment_intent['id'],
        status="canceled",
        metadata={"webhook_processed_at": datetime.utcnow().isoformat()}
    )