"""
Webhook processing tests for the PayPal flow: signature verification
(fail-closed), idempotent delivery, state transitions, and exactly-once
credit grants.
"""

import json
import uuid
from decimal import Decimal

import pytest

from atlas_db.models.billing import (
    BillingCycle,
    BillingCycle,
    CreditAccount,
    CreditTransaction,
    Payment,
    PaymentProvider,
    PaymentStatus,
    Price,
    Product,
    WebhookEvent,
)
from atlas_db.models.core import Organization
from services.billing.registry import GatewayRegistry
from services.billing.service import BillingService


class FakePayPalGateway:
    def __init__(self):
        self.verified_payloads: list[bytes] = []
        self.valid = True

    def verify_webhook_signature(self, payload, signature, headers=None):
        self.verified_payloads.append(payload)
        if not self.valid:
            raise ValueError("Invalid PayPal webhook signature")
        return json.loads(payload)

    def create_checkout_session(self, *args, **kwargs):
        raise NotImplementedError

    def capture_payment(self, *args, **kwargs):
        raise NotImplementedError

    def get_payment(self, *args, **kwargs):
        raise NotImplementedError

    def cancel_subscription(self, provider_subscription_id):
        return False

    def refund_payment(self, provider_payment_id, amount):
        return False


@pytest.fixture()
def org(session):
    org = Organization(name="Test Org", slug=f"test-org-{uuid.uuid4().hex[:8]}")
    session.add(org)
    session.commit()
    return org


@pytest.fixture()
def price(session, org):
    product = Product(name="Test Product", is_active=True)
    session.add(product)
    session.flush()
    price = Price(
        product_id=product.id,
        name="Pro",
        amount=Decimal("50.00"),
        currency="USD",
        billing_cycle=BillingCycle.ONE_TIME,
        is_active=True,
    )
    session.add(price)
    session.commit()
    return price


@pytest.fixture()
def fake_gateway(monkeypatch):
    gateway = FakePayPalGateway()

    def _get_gateway(provider):
        assert provider == PaymentProvider.PAYPAL
        return gateway

    monkeypatch.setattr(GatewayRegistry, "get_gateway", staticmethod(_get_gateway))
    return gateway


@pytest.fixture()
def service(session):
    return BillingService(session)


def _payment_row(session, org_id, status=PaymentStatus.CREATED, **kwargs):
    payment = Payment(
        org_id=org_id,
        amount=Decimal("50.00"),
        currency="USD",
        status=status,
        provider=PaymentProvider.PAYPAL,
        **kwargs,
    )
    session.add(payment)
    session.commit()
    return payment


def _capture_completed_event(resource_id="CAP-1", order_id="ORDER-1", event_id="WH-1"):
    return {
        "id": event_id,
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {
            "id": resource_id,
            "status": "COMPLETED",
            "supplementary_data": {"related_ids": {"order_id": order_id}},
        },
    }


class TestWebhookProcessing:
    def test_completed_capture_grants_credit(self, service, session, org, price, fake_gateway):
        payment = _payment_row(
            session, org.id, status=PaymentStatus.PENDING, provider_order_id="ORDER-1"
        )
        event = _capture_completed_event()

        service.process_webhook(PaymentProvider.PAYPAL, json.dumps(event), "sig")

        session.refresh(payment)
        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.provider_payment_id == "CAP-1"
        assert payment.metadata_json["capture_id"] == "CAP-1"

        account = session.query(CreditAccount).filter_by(org_id=org.id).one()
        assert account.balance == Decimal("50.00")
        assert session.query(CreditTransaction).count() == 1

        event_rows = session.query(WebhookEvent).all()
        assert len(event_rows) == 1
        assert event_rows[0].processed is True
        assert event_rows[0].provider_event_id == "WH-1"

    def test_duplicate_delivery_is_idempotent(self, service, session, org, price, fake_gateway):
        payment = _payment_row(
            session, org.id, status=PaymentStatus.PENDING, provider_order_id="ORDER-1"
        )
        event = _capture_completed_event()

        service.process_webhook(PaymentProvider.PAYPAL, json.dumps(event), "sig")
        service.process_webhook(PaymentProvider.PAYPAL, json.dumps(event), "sig")

        assert session.query(WebhookEvent).count() == 1
        assert session.query(CreditTransaction).count() == 1
        assert session.query(CreditAccount).one().balance == Decimal("50.00")

    def test_invalid_signature_is_rejected(self, service, session, org, price, fake_gateway):
        fake_gateway.valid = False
        event = _capture_completed_event()

        with pytest.raises(ValueError, match="signature"):
            service.process_webhook(PaymentProvider.PAYPAL, json.dumps(event), "bad-sig")

        assert session.query(WebhookEvent).count() == 0
        assert session.query(CreditTransaction).count() == 0

    def test_unknown_payment_is_ignored(self, service, session, org, price, fake_gateway):
        event = _capture_completed_event(order_id="NO-SUCH-ORDER")

        service.process_webhook(PaymentProvider.PAYPAL, json.dumps(event), "sig")

        assert session.query(WebhookEvent).count() == 1
        assert session.query(CreditTransaction).count() == 0

    def test_denied_capture_marks_failed(self, service, session, org, price, fake_gateway):
        payment = _payment_row(
            session, org.id, status=PaymentStatus.PENDING, provider_order_id="ORDER-1"
        )
        event = {
            "id": "WH-2",
            "event_type": "PAYMENT.CAPTURE.DENIED",
            "resource": {
                "id": "CAP-1",
                "status": "DENIED",
                "supplementary_data": {"related_ids": {"order_id": "ORDER-1"}},
            },
        }

        service.process_webhook(PaymentProvider.PAYPAL, json.dumps(event), "sig")

        session.refresh(payment)
        assert payment.status == PaymentStatus.FAILED
        assert session.query(CreditTransaction).count() == 0

    def test_refund_event_marks_refunded(self, service, session, org, price, fake_gateway):
        payment = _payment_row(
            session, org.id, status=PaymentStatus.SUCCEEDED, provider_order_id="ORDER-1"
        )
        event = {
            "id": "WH-3",
            "event_type": "PAYMENT.CAPTURE.REFUNDED",
            "resource": {
                "id": "CAP-1",
                "status": "REFUNDED",
                "supplementary_data": {"related_ids": {"order_id": "ORDER-1"}},
            },
        }

        service.process_webhook(PaymentProvider.PAYPAL, json.dumps(event), "sig")

        session.refresh(payment)
        assert payment.status == PaymentStatus.REFUNDED

    def test_order_approved_marks_pending(self, service, session, org, price, fake_gateway):
        payment = _payment_row(
            session, org.id, status=PaymentStatus.CREATED, provider_order_id="ORDER-1"
        )
        event = {
            "id": "WH-4",
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "resource": {"id": "ORDER-1", "status": "APPROVED"},
        }

        service.process_webhook(PaymentProvider.PAYPAL, json.dumps(event), "sig")

        session.refresh(payment)
        assert payment.status == PaymentStatus.PENDING

    def test_webhook_after_capture_does_not_double_grant(
        self, service, session, org, price, fake_gateway
    ):
        payment = _payment_row(
            session, org.id, status=PaymentStatus.CREATED, provider_order_id="ORDER-1"
        )
        # Simulate the frontend capture flow first: gateway returns a completed capture.
        from services.billing.gateways.base import CaptureResult

        capture_result = CaptureResult(
            capture_id="CAP-1", status="COMPLETED", amount=Decimal("50.00"), currency="USD"
        )
        real_gateway = fake_gateway
        fake_gateway.capture_payment = lambda *a, **kw: capture_result  # type: ignore[attr-defined]
        service.capture_payment(org.id, payment.id)
        assert session.query(CreditTransaction).count() == 1

        # Late-arriving webhook for the same capture must not double-grant.
        event = _capture_completed_event()
        service.process_webhook(PaymentProvider.PAYPAL, json.dumps(event), "sig")

        assert session.query(CreditTransaction).count() == 1
        assert session.query(CreditAccount).one().balance == Decimal("50.00")
        session.refresh(payment)
        assert payment.status == PaymentStatus.SUCCEEDED
