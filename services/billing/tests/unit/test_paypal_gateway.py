"""
PayPalGateway unit tests — all PayPal REST traffic is simulated with
httpx.MockTransport. No live PayPal calls are made.
"""

from decimal import Decimal
from typing import Callable

import httpx
import pytest

from apps.backend.config import settings
from services.billing.gateways.paypal_provider import PayPalGateway

ORDER_BODY = {
    "id": "ORDER-1",
    "status": "CREATED",
    "links": [
        {"href": "https://paypal.example/approve/ORDER-1", "rel": "approve", "method": "GET"}
    ],
}

CAPTURE_BODY = {
    "id": "ORDER-1",
    "status": "COMPLETED",
    "purchase_units": [
        {
            "payments": {
                "captures": [
                    {
                        "id": "CAP-1",
                        "status": "COMPLETED",
                        "amount": {"currency_code": "USD", "value": "50.00"},
                    }
                ]
            }
        }
    ],
}


def _token_handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/v1/oauth2/token"
    assert request.headers["authorization"].startswith("Basic ")
    return httpx.Response(200, json={"access_token": "TOKEN-1", "expires_in": 3600})


def _routed(
    api_handler: Callable[[httpx.Request], httpx.Response],
) -> Callable[[httpx.Request], httpx.Response]:
    """Dispatch OAuth calls to the token handler, everything else to the API handler."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth2/token":
            return _token_handler(request)
        return api_handler(request)

    return handler


def make_gateway(
    handler: Callable[[httpx.Request], httpx.Response], monkeypatch: pytest.MonkeyPatch
) -> PayPalGateway:
    monkeypatch.setattr(settings, "paypal_environment", "sandbox")
    monkeypatch.setattr(settings, "paypal_client_id", "test-client-id")
    monkeypatch.setattr(settings, "paypal_client_secret", "test-client-secret")
    monkeypatch.setattr(settings, "paypal_webhook_id", "WH-1")
    return PayPalGateway(transport=httpx.MockTransport(handler))


class TestOAuth:
    def test_token_acquisition_and_caching(self, monkeypatch):
        token_calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/oauth2/token":
                token_calls["count"] += 1
                return _token_handler(request)
            return httpx.Response(201, json=ORDER_BODY)

        gateway = make_gateway(handler, monkeypatch)

        result1 = gateway.create_checkout_session(
            price_id="P-1",
            org_id=__import__("uuid").uuid4(),
            amount=Decimal("50.00"),
            currency="USD",
            success_url="https://atlas/success",
            cancel_url="https://atlas/cancel",
        )
        result2 = gateway.create_checkout_session(
            price_id="P-1",
            org_id=__import__("uuid").uuid4(),
            amount=Decimal("50.00"),
            currency="USD",
            success_url="https://atlas/success",
            cancel_url="https://atlas/cancel",
        )

        assert result1.session_id == "ORDER-1"
        assert result1.url == "https://paypal.example/approve/ORDER-1"
        assert result2.session_id == "ORDER-1"
        assert token_calls["count"] == 1  # token fetched once and reused

    def test_oauth_failure_raises_value_error(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "invalid_client"})

        gateway = make_gateway(handler, monkeypatch)
        with pytest.raises(ValueError, match="authentication failed"):
            gateway.create_checkout_session(
                price_id="P-1",
                org_id=__import__("uuid").uuid4(),
                amount=Decimal("50.00"),
                currency="USD",
                success_url="https://atlas/success",
                cancel_url="https://atlas/cancel",
            )


class TestCreateOrder:
    def test_success_returns_approval_url(self, monkeypatch):
        gateway = make_gateway(
            _routed(lambda request: httpx.Response(201, json=ORDER_BODY)), monkeypatch
        )
        result = gateway.create_checkout_session(
            price_id="P-1",
            org_id=__import__("uuid").uuid4(),
            amount=Decimal("50.00"),
            currency="USD",
            success_url="https://atlas/success",
            cancel_url="https://atlas/cancel",
        )
        assert result.session_id == "ORDER-1"
        assert result.url.startswith("https://paypal.example/approve/")

    def test_failure_raises_value_error(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/oauth2/token":
                return _token_handler(request)
            return httpx.Response(500, json={"name": "INTERNAL_SERVER_ERROR"})

        gateway = make_gateway(handler, monkeypatch)
        with pytest.raises(ValueError, match="order creation failed"):
            gateway.create_checkout_session(
                price_id="P-1",
                org_id=__import__("uuid").uuid4(),
                amount=Decimal("50.00"),
                currency="USD",
                success_url="https://atlas/success",
                cancel_url="https://atlas/cancel",
            )

    def test_malformed_response_raises_value_error(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/oauth2/token":
                return _token_handler(request)
            return httpx.Response(201, json={"status": "CREATED"})  # no id

        gateway = make_gateway(handler, monkeypatch)
        with pytest.raises(ValueError, match="no order id"):
            gateway.create_checkout_session(
                price_id="P-1",
                org_id=__import__("uuid").uuid4(),
                amount=Decimal("50.00"),
                currency="USD",
                success_url="https://atlas/success",
                cancel_url="https://atlas/cancel",
            )

    def test_amount_formatted_with_two_decimals(self, monkeypatch):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/oauth2/token":
                return _token_handler(request)
            captured["body"] = request.read().decode("utf-8")
            return httpx.Response(201, json=ORDER_BODY)

        gateway = make_gateway(handler, monkeypatch)
        gateway.create_checkout_session(
            price_id="P-1",
            org_id=__import__("uuid").uuid4(),
            amount=Decimal("49.5"),
            currency="USD",
            success_url="https://atlas/success",
            cancel_url="https://atlas/cancel",
        )
        assert '"value":"49.50"' in captured["body"]


class TestCapture:
    def test_capture_success(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/oauth2/token":
                return _token_handler(request)
            return httpx.Response(200, json=CAPTURE_BODY)

        gateway = make_gateway(handler, monkeypatch)
        result = gateway.capture_payment("ORDER-1", Decimal("50.00"), "USD")

        assert result.capture_id == "CAP-1"
        assert result.status == "COMPLETED"
        assert result.amount == Decimal("50.00")
        assert result.currency == "USD"

    def test_capture_failure_raises_value_error(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/oauth2/token":
                return _token_handler(request)
            return httpx.Response(422, json={"name": "UNPROCESSABLE_ENTITY"})

        gateway = make_gateway(handler, monkeypatch)
        with pytest.raises(ValueError, match="capture failed"):
            gateway.capture_payment("ORDER-1", Decimal("50.00"), "USD")

    def test_capture_without_capture_record_raises(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/oauth2/token":
                return _token_handler(request)
            return httpx.Response(200, json={"id": "ORDER-1", "status": "COMPLETED"})

        gateway = make_gateway(handler, monkeypatch)
        with pytest.raises(ValueError, match="no capture record"):
            gateway.capture_payment("ORDER-1", Decimal("50.00"), "USD")


class TestReconcile:
    def test_get_payment_success(self, monkeypatch):
        gateway = make_gateway(
            _routed(lambda request: httpx.Response(200, json=ORDER_BODY)), monkeypatch
        )
        order = gateway.get_payment("ORDER-1")
        assert order["id"] == "ORDER-1"

    def test_get_payment_failure_raises(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/oauth2/token":
                return _token_handler(request)
            return httpx.Response(404, json={"name": "RESOURCE_NOT_FOUND"})

        gateway = make_gateway(handler, monkeypatch)
        with pytest.raises(ValueError, match="order lookup failed"):
            gateway.get_payment("MISSING")


class TestNetworkFailures:
    def test_timeout_raises_value_error(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("boom", request=request)

        gateway = make_gateway(handler, monkeypatch)
        with pytest.raises(ValueError, match="authentication failed"):
            gateway.create_checkout_session(
                price_id="P-1",
                org_id=__import__("uuid").uuid4(),
                amount=Decimal("50.00"),
                currency="USD",
                success_url="https://atlas/success",
                cancel_url="https://atlas/cancel",
            )


class TestWebhookVerification:
    EVENT = {
        "id": "WH-1",
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {"id": "CAP-1"},
    }

    def test_verification_success_returns_event(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/oauth2/token":
                return _token_handler(request)
            if request.url.path == "/v1/notifications/verify-webhook-signature":
                body = __import__("json").loads(request.read().decode("utf-8"))
                assert body["webhook_id"] == "WH-1"
                assert body["transmission_id"] == "TX-1"
                return httpx.Response(200, json={"verification_status": "SUCCESS"})
            return httpx.Response(500)

        gateway = make_gateway(handler, monkeypatch)
        headers = {
            "paypal-transmission-id": "TX-1",
            "paypal-transmission-time": "2026-08-20T00:00:00Z",
            "paypal-transmission-sig": "sig",
            "paypal-cert-url": "https://cert.example",
            "paypal-auth-algo": "SHA256withRSA",
        }
        event = gateway.verify_webhook_signature(
            __import__("json").dumps(self.EVENT), "sig", headers
        )
        assert event["id"] == "WH-1"

    def test_verification_failure_raises(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/oauth2/token":
                return _token_handler(request)
            return httpx.Response(200, json={"verification_status": "FAILURE"})

        gateway = make_gateway(handler, monkeypatch)
        with pytest.raises(ValueError, match="Invalid PayPal webhook signature"):
            gateway.verify_webhook_signature(__import__("json").dumps(self.EVENT), "sig")

    def test_verification_without_webhook_id_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "paypal_webhook_id", "")
        monkeypatch.setattr(settings, "paypal_environment", "sandbox")
        monkeypatch.setattr(settings, "paypal_client_id", "x")
        monkeypatch.setattr(settings, "paypal_client_secret", "y")
        gateway = PayPalGateway(transport=httpx.MockTransport(_token_handler))
        with pytest.raises(ValueError, match="not configured"):
            gateway.verify_webhook_signature(__import__("json").dumps(self.EVENT), "sig")


class TestLifecycle:
    def test_cancel_subscription_unsupported(self, monkeypatch):
        gateway = make_gateway(_routed(lambda request: httpx.Response(500)), monkeypatch)
        assert gateway.cancel_subscription("SUB-1") is False

    def test_refund_success(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(201, json={"id": "REF-1"})

        gateway = make_gateway(_routed(handler), monkeypatch)
        assert gateway.refund_payment("CAP-1", Decimal("50.00")) is True

    def test_refund_failure(self, monkeypatch):
        gateway = make_gateway(_routed(lambda request: httpx.Response(500)), monkeypatch)
        assert gateway.refund_payment("CAP-1", Decimal("50.00")) is False
