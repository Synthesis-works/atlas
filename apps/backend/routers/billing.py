import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from apps.backend.dependencies import get_db_session as get_db, require_authenticated
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.billing import (
    CaptureResponse,
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

router = APIRouter(prefix="/billing", tags=["Billing"])


def _resolve_org_id(claims: TokenClaims) -> uuid.UUID:
    """
    Resolve the tenant organization from the authenticated JWT claims.

    Checkout/payment state is tenant-scoped: every org-scoped billing route
    derives the organization from the token, never from the client.
    """
    org_id = claims.organization_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organization context on token",
        )
    return org_id


@router.get("/plans", response_model=list[ProductResponse])
def get_plans(db: Session = Depends(get_db)):
    """
    List all active products and their prices/plans.
    Public: the pricing page renders plans before authentication.
    """
    repo = BillingRepository(db)
    products = repo.list_active_products_with_prices()

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
def checkout(
    request: CheckoutRequest,
    claims: TokenClaims = Depends(require_authenticated),
    db: Session = Depends(get_db),
):
    """
    Create a checkout session for a specific plan.

    The organization is resolved from the authenticated token; the amount and
    currency are derived server-side from the Atlas Price.
    """
    org_id = _resolve_org_id(claims)

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
        payment = service.repo.get_payment_by_provider_order_id(result.session_id)
        return CheckoutResponse(
            session_id=result.session_id,
            url=result.url,
            payment_id=payment.id if payment else None,
            provider=request.provider,
        )
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/capture/{payment_id}", response_model=CaptureResponse)
def capture(
    payment_id: uuid.UUID,
    claims: TokenClaims = Depends(require_authenticated),
    db: Session = Depends(get_db),
):
    """
    Capture an approved PayPal order server-side.

    Authenticated and tenant-scoped; grants credits only after the provider
    confirms the capture and the amounts match the Atlas payment.
    """
    org_id = _resolve_org_id(claims)
    service = BillingService(db)
    result = service.capture_payment(org_id, payment_id)
    payment = service.repo.get_payment(payment_id)
    return CaptureResponse(
        payment_id=payment_id,
        status=payment.status if payment else None,
        capture_id=result.capture_id,
        provider_order_id=payment.provider_order_id if payment else None,
        amount=result.amount,
        currency=result.currency,
    )


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe Webhook Endpoint. Unauthenticated: authenticity comes from the
    verified webhook signature.
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    try:
        service = BillingService(db)
        service.process_webhook(PaymentProvider.STRIPE, payload, signature, dict(request.headers))
        return {"status": "success"}
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Razorpay Webhook Endpoint. Unauthenticated: authenticity comes from the
    verified webhook signature.
    """
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    try:
        service = BillingService(db)
        service.process_webhook(PaymentProvider.RAZORPAY, payload, signature, dict(request.headers))
        return {"status": "success"}
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhooks/paypal")
async def paypal_webhook(request: Request, db: Session = Depends(get_db)):
    """
    PayPal Webhook Endpoint.

    Unauthenticated: authenticity is established by verifying the event against
    the PayPal verification API using the transmission headers and the
    configured PAYPAL_WEBHOOK_ID. Never trust the raw event body alone.
    """
    payload = await request.body()
    signature = request.headers.get("paypal-transmission-sig", "")

    try:
        service = BillingService(db)
        service.process_webhook(PaymentProvider.PAYPAL, payload, signature, dict(request.headers))
        return {"status": "success"}
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
def get_subscriptions(
    claims: TokenClaims = Depends(require_authenticated), db: Session = Depends(get_db)
):
    repo = BillingRepository(db)
    org_id = _resolve_org_id(claims)
    return repo.get_active_subscriptions_for_org(org_id)


@router.get("/invoices", response_model=list[InvoiceResponse])
def get_invoices(
    claims: TokenClaims = Depends(require_authenticated), db: Session = Depends(get_db)
):
    repo = BillingRepository(db)
    org_id = _resolve_org_id(claims)
    return repo.list_invoices_for_org(org_id)


@router.get("/payments", response_model=list[PaymentResponse])
def get_payments(
    claims: TokenClaims = Depends(require_authenticated), db: Session = Depends(get_db)
):
    repo = BillingRepository(db)
    org_id = _resolve_org_id(claims)
    return repo.list_payments_for_org(org_id)


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: uuid.UUID,
    claims: TokenClaims = Depends(require_authenticated),
    db: Session = Depends(get_db),
):
    """
    Reconcile a payment against the provider's authoritative state.
    Authenticated and tenant-scoped.
    """
    org_id = _resolve_org_id(claims)
    service = BillingService(db)
    payment = service.get_payment_status(org_id, payment_id)
    return payment
