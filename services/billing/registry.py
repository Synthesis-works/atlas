from atlas_db.models.billing import PaymentProvider
from apps.backend.config import settings
from services.billing.gateways.base import PaymentGateway
from services.billing.gateways.stripe_provider import StripeGateway
from services.billing.gateways.razorpay_provider import RazorpayGateway

class GatewayRegistry:
    """
    Registry to manage active payment gateways.
    """

    @classmethod
    def get_gateway(cls, provider: PaymentProvider) -> PaymentGateway:
        if provider == PaymentProvider.STRIPE:
            if not settings.stripe_enabled:
                raise NotImplementedError("Stripe provider is not configured.")
            return StripeGateway()
        elif provider == PaymentProvider.RAZORPAY:
            if not settings.razorpay_enabled:
                raise NotImplementedError("Razorpay provider is not configured.")
            return RazorpayGateway()
        else:
            raise ValueError(f"Unsupported payment provider: {provider}")
