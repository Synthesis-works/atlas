"""
Billing API tests for the PayPal flow: auth enforcement, tenant scoping,
server-side amount derivation, and the public plans endpoint.
"""

import json
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.backend.dependencies import get_db_session, require_authenticated
from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from atlas_db.models.billing import BillingCycle, PaymentProvider, Price, Product
from atlas_db.models.core import Organization
from services.billing.registry import GatewayRegistry
from services.billing.gateways.base import CheckoutSessionResult


class FakePayPalGateway:
    fail_capture_with: str | None = None

    def create_checkout_session(self, price_id, org_id, amount, currency, success_url, cancel_url):
        return CheckoutSessionResult(
            session_id="ORDER-API-1", url="https://paypal.example/approve/ORDER-API-1"
        )

    def capture_payment(self, provider_order_id, amount, currency):
        if self.fail_capture_with:
            raise ValueError(self.fail_capture_with)

        from services.billing.gateways.base import CaptureResult

        return CaptureResult(
            capture_id="CAP-API-1", status="COMPLETED", amount=amount, currency=currency
        )

    def get_payment(self, provider_order_id):
        return {"status": "COMPLETED"}

    def verify_webhook_signature(self, payload, signature, headers=None):
        return json.loads(payload)

    def cancel_subscription(self, provider_subscription_id):
        return False

    def refund_payment(self, provider_payment_id, amount):
        return False


@pytest.fixture()
def client(session, monkeypatch):
    def _override_db():
        yield session

    def _override_auth():
        org_id = session.info.get("billing_test_org_id")
        if org_id is None:
            raise HTTPException(status_code=403, detail="Could not validate credentials")
        return TokenClaims(
            sub=uuid.uuid4(),
            organization_id=org_id,
            exp=9999999999,
            iat=1111111111,
            jti=uuid.uuid4(),
        )

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[require_authenticated] = _override_auth

    def _get_gateway(provider):
        assert provider == PaymentProvider.PAYPAL
        return FakePayPalGateway()

    monkeypatch.setattr(GatewayRegistry, "get_gateway", staticmethod(_get_gateway))

    # Plain TestClient (no context manager) so the lifespan's real database
    # initialization is skipped; DB access is overridden above.
    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def org_and_price(session):
    org = Organization(name="API Org", slug=f"api-org-{uuid.uuid4().hex[:8]}")
    session.add(org)
    session.flush()
    session.info["billing_test_org_id"] = org.id
    product = Product(name="API Product", is_active=True)
    session.add(product)
    session.flush()
    price = Price(
        product_id=product.id,
        name="Pro",
        amount=Decimal("75.00"),
        currency="USD",
        billing_cycle=BillingCycle.ONE_TIME,
        is_active=True,
    )
    session.add(price)
    session.commit()
    return org, price


class TestAuthEnforcement:
    def test_checkout_without_token_is_rejected(self, client):
        response = client.post(
            "/api/v1/billing/checkout",
            json={
                "plan_id": str(uuid.uuid4()),
                "provider": "paypal",
                "success_url": "https://atlas/success",
                "cancel_url": "https://atlas/cancel",
            },
        )
        assert response.status_code == 403

    def test_payments_without_token_is_rejected(self, client):
        response = client.get("/api/v1/billing/payments")
        assert response.status_code == 403

    def test_capture_without_token_is_rejected(self, client):
        response = client.post(f"/api/v1/billing/capture/{uuid.uuid4()}")
        assert response.status_code == 403


class TestPlansEndpoint:
    def test_plans_are_public(self, client, org_and_price):
        response = client.get("/api/v1/billing/plans")
        assert response.status_code == 200
        products = response.json()
        assert len(products) == 1
        assert products[0]["plans"][0]["amount"] == "75.00"


class TestCheckoutApi:
    def test_checkout_creates_paypal_session(self, client, session, org_and_price):
        org, price = org_and_price
        response = client.post(
            "/api/v1/billing/checkout",
            json={
                "plan_id": str(price.id),
                "provider": "paypal",
                "success_url": "https://atlas/success",
                "cancel_url": "https://atlas/cancel",
                "idempotency_key": "api-idem-1",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["session_id"] == "ORDER-API-1"
        assert body["provider"] == "paypal"
        assert body["payment_id"] is not None

    def test_checkout_ignores_client_supplied_amount(self, client, session, org_and_price):
        org, price = org_and_price
        response = client.post(
            "/api/v1/billing/checkout",
            json={
                "plan_id": str(price.id),
                "provider": "paypal",
                "success_url": "https://atlas/success",
                "cancel_url": "https://atlas/cancel",
                "amount": "0.01",
                "currency": "EUR",
            },
        )
        assert response.status_code == 200
        payments = client.get("/api/v1/billing/payments").json()
        assert len(payments) == 1
        assert Decimal(payments[0]["amount"]) == Decimal("75.00")
        assert payments[0]["currency"] == "USD"

    def test_checkout_unknown_plan_returns_404(self, client, session, org_and_price):
        response = client.post(
            "/api/v1/billing/checkout",
            json={
                "plan_id": str(uuid.uuid4()),
                "provider": "paypal",
                "success_url": "https://atlas/success",
                "cancel_url": "https://atlas/cancel",
            },
        )
        assert response.status_code == 404

    def test_checkout_idempotent_key_reused(self, client, session, org_and_price):
        org, price = org_and_price
        payload = {
            "plan_id": str(price.id),
            "provider": "paypal",
            "success_url": "https://atlas/success",
            "cancel_url": "https://atlas/cancel",
            "idempotency_key": "api-idem-2",
        }
        first = client.post("/api/v1/billing/checkout", json=payload)
        second = client.post("/api/v1/billing/checkout", json=payload)
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["payment_id"] == second.json()["payment_id"]


class TestCaptureApi:
    def test_capture_happy_path(self, client, session, org_and_price):
        org, price = org_and_price
        checkout = client.post(
            "/api/v1/billing/checkout",
            json={
                "plan_id": str(price.id),
                "provider": "paypal",
                "success_url": "https://atlas/success",
                "cancel_url": "https://atlas/cancel",
            },
        ).json()
        payment_id = checkout["payment_id"]

        response = client.post(f"/api/v1/billing/capture/{payment_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "succeeded"
        assert body["capture_id"] == "CAP-API-1"
        assert body["provider_order_id"] == "ORDER-API-1"

    def test_capture_unknown_payment_returns_404(self, client, session, org_and_price):
        response = client.post(f"/api/v1/billing/capture/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_capture_gateway_value_error_returns_structured_400(self, client, session, org_and_price):
        org, price = org_and_price
        checkout = client.post(
            "/api/v1/billing/checkout",
            json={
                "plan_id": str(price.id),
                "provider": "paypal",
                "success_url": "https://atlas/success",
                "cancel_url": "https://atlas/cancel",
            },
        ).json()
        payment_id = checkout["payment_id"]

        FakePayPalGateway.fail_capture_with = "PayPal capture failed"
        try:
            response = client.post(f"/api/v1/billing/capture/{payment_id}")
        finally:
            FakePayPalGateway.fail_capture_with = None

        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["message"] == "PayPal capture failed"
        assert "secret" not in body["error"]["message"].lower()


class TestPaymentApi:
    def test_reconcile_owned_payment(self, client, session, org_and_price):
        org, price = org_and_price
        checkout = client.post(
            "/api/v1/billing/checkout",
            json={
                "plan_id": str(price.id),
                "provider": "paypal",
                "success_url": "https://atlas/success",
                "cancel_url": "https://atlas/cancel",
            },
        ).json()
        payment_id = checkout["payment_id"]

        response = client.get(f"/api/v1/billing/payments/{payment_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["provider"] == "paypal"
        assert body["provider_order_id"] == "ORDER-API-1"

    def test_payment_of_other_org_is_hidden(self, client, session, org_and_price):
        org, price = org_and_price
        checkout = client.post(
            "/api/v1/billing/checkout",
            json={
                "plan_id": str(price.id),
                "provider": "paypal",
                "success_url": "https://atlas/success",
                "cancel_url": "https://atlas/cancel",
            },
        ).json()
        payment_id = checkout["payment_id"]

        from atlas_db.models.billing import Payment

        other_org = Organization(name="Other API Org", slug=f"other-api-{uuid.uuid4().hex[:8]}")
        session.add(other_org)
        session.commit()
        payment = session.get(Payment, uuid.UUID(payment_id))
        payment.org_id = other_org.id  # simulate tenant isolation mismatch
        session.commit()

        response = client.get(f"/api/v1/billing/payments/{payment_id}")
        assert response.status_code == 404


class TestPaypalWebhookApi:
    def test_webhook_endpoint_accepts_event(self, client, session, org_and_price):
        org, price = org_and_price
        checkout = client.post(
            "/api/v1/billing/checkout",
            json={
                "plan_id": str(price.id),
                "provider": "paypal",
                "success_url": "https://atlas/success",
                "cancel_url": "https://atlas/cancel",
            },
        ).json()
        payment_id = checkout["payment_id"]

        event = {
            "id": "WH-API-1",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {
                "id": "CAP-API-1",
                "status": "COMPLETED",
                "supplementary_data": {"related_ids": {"order_id": "ORDER-API-1"}},
            },
        }
        response = client.post(
            "/api/v1/billing/webhooks/paypal",
            content=json.dumps(event),
            headers={"paypal-transmission-sig": "sig"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        payment = client.get(f"/api/v1/billing/payments/{payment_id}").json()
        assert payment["status"] == "succeeded"
