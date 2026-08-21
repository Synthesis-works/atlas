import json
import uuid
from decimal import Decimal
from typing import Any

import stripe
from pydantic import BaseModel

from apps.backend.config import settings
from services.billing.gateways.base import CheckoutSessionResult, PaymentGateway

stripe.api_key = settings.stripe_api_key


class StripeGateway(PaymentGateway):
    def create_checkout_session(
        self,
        price_id: str,
        org_id: uuid.UUID,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        invoice_id: str,
    ) -> CheckoutSessionResult:
        # If price_id exists on Stripe, we use it directly (e.g. for subscriptions).
        # Otherwise, we create a one-time price dynamically or use line_items.

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            mode="subscription" if "recurring" in price_id else "payment",  # simplified logic
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(org_id),
            metadata={"org_id": str(org_id), "invoice_id": invoice_id},
        )
        return CheckoutSessionResult(session_id=session.id, url=session.url or "")

    def verify_webhook_signature(
        self,
        payload: str | bytes,
        signature: str,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        webhook_secret = settings.stripe_webhook_secret
        try:
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
            return dict(event)  # type: ignore[arg-type]
        except ValueError as e:
            raise ValueError("Invalid payload") from e
        except stripe.error.SignatureVerificationError as e:
            raise ValueError("Invalid signature") from e

    def cancel_subscription(self, subscription_id: str) -> bool:
        try:
            stripe.Subscription.delete(subscription_id)  # type: ignore[arg-type]
            return True
        except Exception:
            return False

    def refund_payment(self, payment_id: str, amount: Decimal) -> bool:
        try:
            # Stripe amounts are in cents
            amount_cents = int(amount * 100)
            stripe.Refund.create(payment_intent=payment_id, amount=amount_cents)
            return True
        except Exception:
            return False
