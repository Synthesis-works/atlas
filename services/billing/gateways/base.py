import abc
from typing import Any
from pydantic import BaseModel
import uuid
from decimal import Decimal

class CheckoutSessionResult(BaseModel):
    session_id: str
    url: str

class PaymentGateway(abc.ABC):
    """
    Abstract base class for all payment providers (Stripe, Razorpay, etc.)
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
    ) -> CheckoutSessionResult:
        """
        Creates a checkout session for the customer.
        For subscriptions, price_id corresponds to the provider's plan ID.
        """
        pass

    @abc.abstractmethod
    def verify_webhook_signature(
        self,
        payload: str | bytes,
        signature: str,
    ) -> dict[str, Any]:
        """
        Verifies the webhook signature and returns the parsed payload as a dict.
        Raises an error if the signature is invalid.
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
