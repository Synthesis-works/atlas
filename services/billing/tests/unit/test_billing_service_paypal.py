"""
BillingService unit tests for the PayPal flow: idempotent checkout, capture
with server-side amount validation, exactly-once credit activation, and
payment ownership rules. The gateway is replaced with a fake to keep tests
off the network.
"""

import json
import uuid
from decimal import Decimal

import pytest

from fastapi import HTTPException

from atlas_db.models.billing import (
    BillingCycle,
    CreditAccount,
    CreditTransaction,
    Payment,
    PaymentProvider,
    PaymentStatus,
    Price,
    Product,
)
from atlas_db.models.core import Organization
from services.billing.gateways.base import CaptureResult, CheckoutSessionResult
from services.billing.registry import GatewayRegistry
from services.billing.service import BillingService


class FakePayPalGateway:
    """In-memory stand-in for PayPalGateway; records calls for assertions."""

    def __init__(self):
        self.created: list[tuple] = []
        self.captured: list[tuple] = []
        self.looked_up: list[str] = []
        self.capture_result: CaptureResult | None = None
        self.order_lookup: dict | None = None

    def create_checkout_session(self, price_id, org_id, amount, currency, success_url, cancel_url):
        self.created.append((str(price_id), str(org_id), amount, currency))
        return CheckoutSessionResult(
            session_id="ORDER-1", url="https://paypal.example/approve/ORDER-1"
        )

    def capture_payment(self, provider_order_id, amount, currency):
        self.captured.append((provider_order_id, amount, currency))
        if self.capture_result is not None:
            return self.capture_result
        return CaptureResult(
            capture_id="CAP-1", status="COMPLETED", amount=amount, currency=currency
        )

    def get_payment(self, provider_order_id):
        self.looked_up.append(provider_order_id)
        if self.order_lookup is not None:
            return self.order_lookup
        return {"status": "COMPLETED"}

    def verify_webhook_signature(self, payload, signature, headers=None):
        return json.loads(payload)

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


class TestCheckout:
    def test_creates_pending_payment_with_provider_order(
        self, service, session, org, price, fake_gateway
    ):
        result = service.create_checkout_session(
            org_id=org.id,
            price_id=price.id,
            provider=PaymentProvider.PAYPAL,
            success_url="https://atlas/success",
            cancel_url="https://atlas/cancel",
            idempotency_key="idem-1",
        )

        assert result.session_id == "ORDER-1"
        payment = session.query(Payment).filter_by(idempotency_key="idem-1").one()
        assert payment.provider == PaymentProvider.PAYPAL
        assert payment.provider_order_id == "ORDER-1"
        assert payment.status == PaymentStatus.CREATED
        assert payment.amount == Decimal("50.00")
        assert payment.currency == "USD"

    def test_amount_is_derived_from_price_not_client(
        self, service, session, org, price, fake_gateway
    ):
        service.create_checkout_session(
            org_id=org.id,
            price_id=price.id,
            provider=PaymentProvider.PAYPAL,
            success_url="https://atlas/success",
            cancel_url="https://atlas/cancel",
        )
        price_id, _, amount, currency = fake_gateway.created[0]
        assert Decimal(amount) == price.amount
        assert currency == price.currency

    def test_same_idempotency_key_returns_existing_session(
        self, service, session, org, price, fake_gateway
    ):
        first = service.create_checkout_session(
            org_id=org.id,
            price_id=price.id,
            provider=PaymentProvider.PAYPAL,
            success_url="https://atlas/success",
            cancel_url="https://atlas/cancel",
            idempotency_key="idem-2",
        )
        second = service.create_checkout_session(
            org_id=org.id,
            price_id=price.id,
            provider=PaymentProvider.PAYPAL,
            success_url="https://atlas/success",
            cancel_url="https://atlas/cancel",
            idempotency_key="idem-2",
        )

        assert first.session_id == second.session_id
        assert len(fake_gateway.created) == 1  # gateway called exactly once
        assert session.query(Payment).count() == 1

    def test_distinct_idempotency_keys_create_distinct_payments(
        self, service, session, org, price, fake_gateway
    ):
        service.create_checkout_session(
            org_id=org.id,
            price_id=price.id,
            provider=PaymentProvider.PAYPAL,
            success_url="https://atlas/success",
            cancel_url="https://atlas/cancel",
            idempotency_key="idem-a",
        )
        service.create_checkout_session(
            org_id=org.id,
            price_id=price.id,
            provider=PaymentProvider.PAYPAL,
            success_url="https://atlas/success",
            cancel_url="https://atlas/cancel",
            idempotency_key="idem-b",
        )
        assert session.query(Payment).count() == 2

    def test_inactive_price_is_rejected(self, service, session, org, price):
        price.is_active = False
        session.commit()
        with pytest.raises(HTTPException, match="no longer active"):
            service.create_checkout_session(
                org_id=org.id,
                price_id=price.id,
                provider=PaymentProvider.PAYPAL,
                success_url="https://atlas/success",
                cancel_url="https://atlas/cancel",
            )

    def test_unknown_price_is_rejected(self, service, session, org):
        with pytest.raises(HTTPException, match="not found"):
            service.create_checkout_session(
                org_id=org.id,
                price_id=uuid.uuid4(),
                provider=PaymentProvider.PAYPAL,
                success_url="https://atlas/success",
                cancel_url="https://atlas/cancel",
            )


class TestCapture:
    def test_capture_success_grants_credit_once(self, service, session, org, price, fake_gateway):
        payment = _payment_row(session, org.id, provider_order_id="ORDER-1")
        result = service.capture_payment(org.id, payment.id)

        assert result.capture_id == "CAP-1"
        assert result.status == "COMPLETED"

        session.refresh(payment)
        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.provider_payment_id == "CAP-1"

        account = session.query(CreditAccount).filter_by(org_id=org.id).one()
        assert account.balance == Decimal("50.00")
        transactions = session.query(CreditTransaction).all()
        assert len(transactions) == 1
        assert transactions[0].reference_type == "payment"
        assert transactions[0].reference_id == str(payment.id)

    def test_capture_amount_mismatch_is_rejected(self, service, session, org, price, fake_gateway):
        fake_gateway.capture_result = CaptureResult(
            capture_id="CAP-X", status="COMPLETED", amount=Decimal("1.00"), currency="USD"
        )
        payment = _payment_row(session, org.id, provider_order_id="ORDER-1")
        with pytest.raises(Exception, match="amount"):
            service.capture_payment(org.id, payment.id)
        session.refresh(payment)
        assert payment.status == PaymentStatus.CREATED

    def test_capture_currency_mismatch_is_rejected(
        self, service, session, org, price, fake_gateway
    ):
        fake_gateway.capture_result = CaptureResult(
            capture_id="CAP-X", status="COMPLETED", amount=Decimal("50.00"), currency="EUR"
        )
        payment = _payment_row(session, org.id, provider_order_id="ORDER-1")
        with pytest.raises(Exception, match="currency"):
            service.capture_payment(org.id, payment.id)
        session.refresh(payment)
        assert payment.status == PaymentStatus.CREATED

    def test_capture_of_other_orgs_payment_is_rejected(
        self, service, session, org, price, fake_gateway
    ):
        other_org = Organization(name="Other Org", slug=f"other-org-{uuid.uuid4().hex[:8]}")
        session.add(other_org)
        session.commit()
        payment = _payment_row(session, org.id, provider_order_id="ORDER-1")
        with pytest.raises(Exception, match="not found"):
            service.capture_payment(other_org.id, payment.id)

    def test_duplicate_capture_is_rejected(self, service, session, org, price, fake_gateway):
        payment = _payment_row(session, org.id, provider_order_id="ORDER-1")
        service.capture_payment(org.id, payment.id)
        with pytest.raises(Exception, match="already"):
            service.capture_payment(org.id, payment.id)
        assert session.query(CreditTransaction).count() == 1

    def test_duplicate_capture_attempt_from_two_instances_grants_once(
        self, service, session, org, price, fake_gateway
    ):
        payment = _payment_row(session, org.id, provider_order_id="ORDER-1")
        service.capture_payment(org.id, payment.id)
        second_service = BillingService(session)
        with pytest.raises(HTTPException, match="already"):
            second_service.capture_payment(org.id, payment.id)
        assert session.query(CreditTransaction).count() == 1
        session.refresh(payment)
        assert payment.status == PaymentStatus.SUCCEEDED

    def test_capture_failed_status_is_recorded(self, service, session, org, price, fake_gateway):
        fake_gateway.capture_result = CaptureResult(
            capture_id="CAP-F", status="FAILED", amount=Decimal("50.00"), currency="USD"
        )
        payment = _payment_row(session, org.id, provider_order_id="ORDER-1")
        service.capture_payment(org.id, payment.id)
        session.refresh(payment)
        assert payment.status == PaymentStatus.FAILED


class TestReconciliation:
    def test_pending_payment_matches_completed_order(
        self, service, session, org, price, fake_gateway
    ):
        payment = _payment_row(
            session, org.id, status=PaymentStatus.PENDING, provider_order_id="ORDER-1"
        )
        fake_gateway.order_lookup = {
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

        payment = service.get_payment_status(org.id, payment.id)

        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.provider_payment_id == "CAP-1"
        assert session.query(CreditTransaction).count() == 1

    def test_reconciliation_keeps_failed_order_failed(
        self, service, session, org, price, fake_gateway
    ):
        payment = _payment_row(
            session, org.id, status=PaymentStatus.PENDING, provider_order_id="ORDER-1"
        )
        fake_gateway.order_lookup = {"id": "ORDER-1", "status": "VOIDED"}
        payment = service.get_payment_status(org.id, payment.id)
        assert payment.status == PaymentStatus.FAILED
        assert session.query(CreditTransaction).count() == 0

    def test_reconciliation_respects_ownership(self, service, session, org, price, fake_gateway):
        other_org = Organization(name="Other Org", slug=f"other-org-{uuid.uuid4().hex[:8]}")
        session.add(other_org)
        session.commit()
        payment = _payment_row(
            session, org.id, status=PaymentStatus.PENDING, provider_order_id="ORDER-1"
        )
        with pytest.raises(Exception, match="not found"):
            service.get_payment_status(other_org.id, payment.id)
