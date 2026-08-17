import hmac
import hashlib
import uuid
import razorpay
from decimal import Decimal
from typing import Any

from apps.backend.config import settings
from services.billing.gateways.base import CheckoutSessionResult, PaymentGateway


class RazorpayGateway(PaymentGateway):
    def __init__(self):
        self.client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

    def create_checkout_session(
        self,
        price_id: str,
        org_id: uuid.UUID,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSessionResult:
        # Razorpay expects amounts in smaller units (paise for INR)
        amount_paise = int(amount * 100)

        # We can create an order in Razorpay for a one-time payment
        order = self.client.order.create(
            {
                "amount": amount_paise,
                "currency": currency,
                "receipt": str(org_id),
                "notes": {"org_id": str(org_id), "price_id": price_id},
            }
        )

        # For Razorpay, we don't return a direct hosted URL like Stripe Checkout.
        # Usually, the frontend initiates Razorpay with the `order_id`.
        # However, for consistency with the interface, we'll return the order_id as session_id.
        return CheckoutSessionResult(
            session_id=order["id"],
            url="",  # Razorpay handles UI on the frontend side via JS popup
        )

    def verify_webhook_signature(
        self,
        payload: str | bytes,
        signature: str,
    ) -> dict[str, Any]:
        """
        Verify the signature of the razorpay webhook.
        """
        secret = settings.razorpay_webhook_secret
        if isinstance(payload, bytes):
            payload_str = payload.decode("utf-8")
        else:
            payload_str = payload

        try:
            self.client.utility.verify_webhook_signature(payload_str, signature, secret)
        except razorpay.errors.SignatureVerificationError:
            raise ValueError("Invalid Razorpay signature")

        import json

        return dict(json.loads(payload_str))

    def cancel_subscription(self, subscription_id: str) -> bool:
        try:
            self.client.subscription.cancel(subscription_id)
            return True
        except Exception:
            return False

    def refund_payment(self, payment_id: str, amount: Decimal) -> bool:
        try:
            amount_paise = int(amount * 100)
            self.client.payment.refund(payment_id, amount_paise)
            return True
        except Exception:
            return False
