import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from apps.backend.dependencies import get_db_session as get_db
from apps.backend.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    ProductResponse,
    SubscriptionResponse,
    InvoiceResponse,
    PaymentResponse,
)
from atlas_db.models.billing import PaymentProvider
from atlas_db.repositories.billing import BillingRepository
from services.billing.service import BillingService

# In a real app we'd also import get_current_user / auth deps to extract org_id
# For this scaffold, we'll assume the client sends org_id or it's inferred from context.

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/plans", response_model=list[ProductResponse])
def get_plans(db: Session = Depends(get_db)):
    """
    List all active products and their prices/plans.
    """
    repo = BillingRepository(db)
    # Note: SQLAlchemy returns mapped instances. Using Pydantic from_attributes works easily.
    products = repo.list_active_products_with_prices()

    # We need to map products and their nested prices correctly.
    # Because of the relationship, Pydantic will extract `prices` but the schema calls it `plans`.
    # Let's map it manually or adjust the schema. We'll map manually for simplicity.
    results = []
    for prod in products:
        results.append(
            ProductResponse(
                id=prod.id,
                name=prod.name,
                description=prod.description,
                is_active=prod.is_active,
                plans=prod.prices,
            )
        )
    return results


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(request: CheckoutRequest, db: Session = Depends(get_db)):
    """
    Create a checkout session for a specific plan.
    Requires authentication to infer the organization.
    For this scaffold, we will mock the org_id if not present in context.
    """
    # Mocking org_id for compilation. In production: org_id = current_user.org_id
    org_id = uuid.uuid4()

    try:
        service = BillingService(db)
        result = service.create_checkout_session(
            org_id=org_id,
            price_id=request.plan_id,
            provider=request.provider,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            idempotency_key=request.idempotency_key,
        )
        return result
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe Webhook Endpoint.
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    try:
        service = BillingService(db)
        service.process_webhook(PaymentProvider.STRIPE, payload, signature)
        return {"status": "success"}
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Razorpay Webhook Endpoint.
    """
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    try:
        service = BillingService(db)
        service.process_webhook(PaymentProvider.RAZORPAY, payload, signature)
        return {"status": "success"}
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
def get_subscriptions(db: Session = Depends(get_db)):
    repo = BillingRepository(db)
    org_id = uuid.uuid4()  # Mock org id
    return repo.get_active_subscriptions_for_org(org_id)


@router.get("/invoices", response_model=list[InvoiceResponse])
def get_invoices(db: Session = Depends(get_db)):
    repo = BillingRepository(db)
    org_id = uuid.uuid4()  # Mock org id
    return repo.list_invoices_for_org(org_id)


@router.get("/payments", response_model=list[PaymentResponse])
def get_payments(db: Session = Depends(get_db)):
    repo = BillingRepository(db)
    org_id = uuid.uuid4()  # Mock org id
    return repo.list_payments_for_org(org_id)
