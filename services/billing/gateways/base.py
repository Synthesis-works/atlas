import abc
from decimal import Decimal
from typing import Any

import uuid
from pydantic import BaseModel


class CheckoutSessionResult(BaseModel):
    session_id: str
    url: str


class CaptureResult(BaseModel):
    """
    Provider-neutral result of a server-side payment capture.

    `amount`/`currency` are populated when the provider returns the captured
    amount so the application layer can re-validate it against the Atlas
    `Payment` (never trusting a client-supplied amount).
    """

    capture_id: str
    status: str
    amount: Decimal | None = None
    currency: str | None = None


class PaymentGateway(abc.ABC):
    """
    Abstract base class for all payment providers (Stripe, Razorpay, PayPal, etc.)
    """

    @abc.abstractmethod
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
        """
        Creates a checkout session for the customer.
        For subscriptions, price_id corresponds to the provider's plan ID.

        `invoice_id` must be unique per Atlas payment (never per plan): some
        providers (e.g. PayPal) reject a capture whose invoice_id was already
        used by a previously captured transaction in the merchant account.
        Callers pass a stable, traceable identifier such as ``ATLAS-<payment_id>``.
        """
        pass

    @abc.abstractmethod
    def verify_webhook_signature(
        self,
        payload: str | bytes,
        signature: str,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Verifies the webhook signature and returns the parsed payload as a dict.
        Raises an error if the signature is invalid.

        `headers` carries provider-specific verification headers for providers
        (e.g. PayPal) whose verification scheme needs more than a single
        signature header. Signature-based providers (Stripe, Razorpay) may
        ignore it.
        """
        pass

    @abc.abstractmethod
    def cancel_subscription(self, subscription_id: str) -> bool:
        """
        Cancels an active subscription at the provider.
        """
        pass

    @abc.abstractmethod
    def refund_payment(self, payment_id: str, amount: Decimal) -> bool:
        """
        Refunds a specific payment.
        """
        pass

    # --- Optional capabilities -------------------------------------------------
    # Server-side capture and order/payment lookup are required for the
    # PayPal Checkout flow (create -> approve -> capture) but not for every
    # provider. These methods provide safe defaults so existing implementers
    # keep working unchanged; providers that support the capability override
    # them.

    def capture_payment(
        self,
        provider_order_id: str,
        amount: Decimal,
        currency: str,
    ) -> CaptureResult:
        """
        Captures an approved provider order server-side.

        Default: unsupported. Providers that implement server-side capture
        (e.g. PayPal) override this method.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support server-side capture")

    def get_payment(self, provider_order_id: str) -> dict[str, Any]:
        """
        Retrieves the authoritative state of a provider order/payment.

        Default: unsupported. Providers that implement reconciliation
        (e.g. PayPal) override this method.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support payment lookup")
