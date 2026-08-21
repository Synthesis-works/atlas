import json
import logging
import time
import uuid
from decimal import Decimal
from typing import Any

import httpx

from apps.backend.config import settings
from services.billing.gateways.base import CaptureResult, CheckoutSessionResult, PaymentGateway

logger = logging.getLogger(__name__)

# Currencies that PayPal represents with zero decimal places (minor-unit = 1).
ZERO_DECIMAL_CURRENCIES = frozenset(
    {
        "JPY",
        "KRW",
        "TWD",
        "HUF",
        "CLP",
        "ISK",
        "DJF",
        "RWF",
        "UGX",
        "VND",
        "VUV",
        "XAF",
        "XOF",
        "XPF",
    }
)

PAYPAL_API_BASE_URLS = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "live": "https://api-m.paypal.com",
}


def _format_amount(amount: Decimal, currency: str) -> str:
    """Format a Decimal amount into PayPal's string 'value' representation."""
    if currency.upper() in ZERO_DECIMAL_CURRENCIES:
        return str(int(amount))
    return f"{amount:.2f}"


class PayPalGateway(PaymentGateway):
    """
    PayPal Checkout (Orders v2) payment provider backed by the PayPal REST API.

    The gateway talks directly to the PayPal REST API over ``httpx``; no PayPal
    SDK is required. The Atlas domain/BillingService layer only ever interacts
    with the provider-neutral ``PaymentGateway`` interface, never PayPal types.

    Environment selection is driven by ``PAYPAL_ENVIRONMENT`` (sandbox|live).
    The OAuth client-credentials token is cached for its lifetime and refreshed
    automatically. The Client Secret never leaves the server.
    """

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._base_url = PAYPAL_API_BASE_URLS.get(
            settings.paypal_environment, PAYPAL_API_BASE_URLS["sandbox"]
        )
        self._transport = transport
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=30.0, transport=self._transport)

    # ------------------------------------------------------------------ auth

    def _get_access_token(self) -> str:
        """
        Return a cached PayPal OAuth access token, refreshing it when expired.
        """
        now = time.monotonic()
        if self._access_token and now < self._token_expires_at:
            return self._access_token

        try:
            with self._client() as client:
                response = client.post(
                    f"{self._base_url}/v1/oauth2/token",
                    data={"grant_type": "client_credentials"},
                    auth=(settings.paypal_client_id, settings.paypal_client_secret),
                    headers={"Accept": "application/json"},
                )
        except httpx.HTTPError as exc:
            logger.error("PayPal OAuth token request failed: %s", type(exc).__name__)
            raise ValueError("PayPal authentication failed") from exc

        if response.status_code != 200:
            logger.error("PayPal OAuth token request returned %s", response.status_code)
            raise ValueError("PayPal authentication failed")

        body = response.json()
        token = str(body.get("access_token") or "")
        if not token:
            raise ValueError("PayPal authentication failed: no access token returned")

        self._access_token = token
        # Cache slightly under the provider expiry to avoid racing the boundary.
        self._token_expires_at = now + max(int(body.get("expires_in", 3600)) - 60, 60)
        return token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ------------------------------------------------------------- checkout

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
        Create a PayPal Orders v2 order (intent=CAPTURE) and return its id plus
        the approval URL for the frontend.

        `invoice_id` is stored on the purchase unit and must be unique per
        Atlas payment: PayPal validates invoice_id uniqueness against already
        captured transactions at capture time (DUPLICATE_INVOICE_ID).
        """
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": price_id,
                    "custom_id": str(org_id),
                    "invoice_id": invoice_id[:127],
                    "amount": {
                        "currency_code": currency.upper(),
                        "value": _format_amount(amount, currency),
                    },
                }
            ],
            "application_context": {
                "brand_name": "Atlas",
                "return_url": success_url,
                "cancel_url": cancel_url,
                "user_action": "PAY_NOW",
            },
        }

        try:
            with self._client() as client:
                response = client.post(
                    f"{self._base_url}/v2/checkout/orders",
                    json=payload,
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            logger.error("PayPal create order request failed: %s", type(exc).__name__)
            raise ValueError("PayPal order creation failed") from exc

        if response.status_code not in (200, 201):
            logger.error("PayPal create order returned %s", response.status_code)
            raise ValueError("PayPal order creation failed")

        body = response.json()
        order_id = body.get("id")
        if not order_id:
            raise ValueError("PayPal order creation failed: no order id returned")

        approval_url = ""
        for link in body.get("links", []):
            if link.get("rel") in ("approve", "payer-action"):
                approval_url = link.get("href", "")
                break

        return CheckoutSessionResult(session_id=order_id, url=approval_url)

    # --------------------------------------------------------------- capture

    def capture_payment(
        self,
        provider_order_id: str,
        amount: Decimal,
        currency: str,
    ) -> CaptureResult:
        """
        Capture an approved PayPal order server-side and return the captured
        amount/currency for the application layer to re-validate.
        """
        try:
            with self._client() as client:
                response = client.post(
                    f"{self._base_url}/v2/checkout/orders/{provider_order_id}/capture",
                    json={},
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            logger.error("PayPal capture request failed: %s", type(exc).__name__)
            raise ValueError("PayPal capture failed") from exc

        if response.status_code not in (200, 201):
            logger.error("PayPal capture returned %s", response.status_code)
            raise ValueError("PayPal capture failed")

        body = response.json()
        captures = body.get("purchase_units", [{}])[0].get("payments", {}).get("captures", [])
        if not captures:
            raise ValueError("PayPal capture failed: no capture record returned")

        capture = captures[0]
        captured_amount = capture.get("amount", {})
        return CaptureResult(
            capture_id=capture.get("id", ""),
            status=capture.get("status", ""),
            amount=Decimal(str(captured_amount.get("value", "0")))
            if captured_amount.get("value")
            else None,
            currency=captured_amount.get("currency_code"),
        )

    # ------------------------------------------------------------ reconcile

    def get_payment(self, provider_order_id: str) -> dict[str, Any]:
        """
        Retrieve the authoritative PayPal order state for reconciliation.
        """
        try:
            with self._client() as client:
                response = client.get(
                    f"{self._base_url}/v2/checkout/orders/{provider_order_id}",
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            logger.error("PayPal get order request failed: %s", type(exc).__name__)
            raise ValueError("PayPal order lookup failed") from exc

        if response.status_code != 200:
            logger.error("PayPal get order returned %s", response.status_code)
            raise ValueError("PayPal order lookup failed")

        return dict(response.json())

    # -------------------------------------------------------------- webhooks

    def verify_webhook_signature(
        self,
        payload: str | bytes,
        signature: str,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Verify a PayPal webhook event using the PayPal verification API.

        Unlike Stripe/Razorpay (symmetric HMAC), PayPal's scheme requires the
        transmission headers plus the configured webhook id. The raw payload is
        passed to ``POST /v1/notifications/verify-webhook-signature``; the event
        is only accepted when ``verification_status`` is ``SUCCESS``.
        """
        webhook_id = settings.paypal_webhook_id
        if not webhook_id:
            raise ValueError("PayPal webhook verification is not configured")

        headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
        try:
            event_obj = json.loads(payload) if isinstance(payload, bytes) else json.loads(payload)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid PayPal webhook payload") from exc

        verify_payload = {
            "auth_algo": headers.get("paypal-auth-algo", ""),
            "cert_url": headers.get("paypal-cert-url", ""),
            "transmission_id": headers.get("paypal-transmission-id", ""),
            "transmission_sig": headers.get("paypal-transmission-sig", ""),
            "transmission_time": headers.get("paypal-transmission-time", ""),
            "webhook_id": webhook_id,
            "webhook_event": event_obj,
        }

        try:
            with self._client() as client:
                response = client.post(
                    f"{self._base_url}/v1/notifications/verify-webhook-signature",
                    json=verify_payload,
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            logger.error("PayPal webhook verification request failed: %s", type(exc).__name__)
            raise ValueError("PayPal webhook verification failed") from exc

        if response.status_code != 200:
            logger.error("PayPal webhook verification returned %s", response.status_code)
            raise ValueError("PayPal webhook verification failed")

        verification_status = response.json().get("verification_status")
        if verification_status != "SUCCESS":
            logger.warning("PayPal webhook verification status: %s", verification_status)
            raise ValueError("Invalid PayPal webhook signature")

        return dict(event_obj)

    # -------------------------------------------------------------- lifecycle

    def cancel_subscription(self, subscription_id: str) -> bool:
        # PayPal Checkout (Orders v2) does not manage subscriptions; Atlas does
        # not use PayPal Billing Agreements. Report as unsupported without
        # pretending to cancel anything at the provider.
        return False

    def refund_payment(self, payment_id: str, amount: Decimal) -> bool:
        # PayPal's capture-refund API does not require a currency for a full
        # refund (empty body refunds the entire capture). The gateway contract
        # does not carry a currency, so Atlas refunds the full capture amount.
        try:
            with self._client() as client:
                response = client.post(
                    f"{self._base_url}/v2/payments/captures/{payment_id}/refund",
                    json={},
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            logger.error("PayPal refund request failed: %s", type(exc).__name__)
            return False

        return response.status_code in (200, 201)
