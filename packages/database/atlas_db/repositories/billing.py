import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session
from atlas_db.core.base import utcnow
from atlas_db.models.billing import (
    Product,
    Price,
    Subscription,
    Invoice,
    Payment,
    Refund,
    WebhookEvent,
    CreditAccount,
    CreditTransaction,
    Feature,
    PriceFeature,
    UsageRecord,
)

class BillingRepository:
    """
    Repository for all billing related data access operations.
    """

    def __init__(self, session: Session):
        self.session = session

    # --- Products and Prices ---
    def get_product(self, product_id: uuid.UUID) -> Product | None:
        return self.session.get(Product, product_id)

    def list_active_products_with_prices(self) -> Sequence[Product]:
        stmt = (
            select(Product)
            .where(Product.is_active == True)
        )
        return self.session.scalars(stmt).all()

    def get_price(self, price_id: uuid.UUID) -> Price | None:
        return self.session.get(Price, price_id)

    def get_price_by_provider_id(self, provider_price_id: str) -> Price | None:
        stmt = select(Price).where(Price.provider_price_id == provider_price_id)
        return self.session.scalars(stmt).first()

    # --- Subscriptions ---
    def create_subscription(self, subscription: Subscription) -> Subscription:
        self.session.add(subscription)
        self.session.flush()
        return subscription

    def get_subscription(self, subscription_id: uuid.UUID) -> Subscription | None:
        return self.session.get(Subscription, subscription_id)

    def get_subscription_by_provider_id(self, provider_subscription_id: str) -> Subscription | None:
        stmt = select(Subscription).where(Subscription.provider_subscription_id == provider_subscription_id)
        return self.session.scalars(stmt).first()

    def get_active_subscriptions_for_org(self, org_id: uuid.UUID) -> Sequence[Subscription]:
        stmt = select(Subscription).where(
            Subscription.org_id == org_id,
            Subscription.status.in_(["active", "trialing"])
        )
        return self.session.scalars(stmt).all()

    # --- Invoices ---
    def create_invoice(self, invoice: Invoice) -> Invoice:
        self.session.add(invoice)
        self.session.flush()
        return invoice
        
    def get_invoice_by_provider_id(self, provider_invoice_id: str) -> Invoice | None:
        stmt = select(Invoice).where(Invoice.provider_invoice_id == provider_invoice_id)
        return self.session.scalars(stmt).first()

    def list_invoices_for_org(self, org_id: uuid.UUID) -> Sequence[Invoice]:
        stmt = select(Invoice).where(Invoice.org_id == org_id)
        return self.session.scalars(stmt).all()

    # --- Payments ---
    def create_payment(self, payment: Payment) -> Payment:
        self.session.add(payment)
        self.session.flush()
        return payment

    def get_payment(self, payment_id: uuid.UUID) -> Payment | None:
        return self.session.get(Payment, payment_id)

    def get_payment_by_provider_id(self, provider_payment_id: str) -> Payment | None:
        stmt = select(Payment).where(Payment.provider_payment_id == provider_payment_id)
        return self.session.scalars(stmt).first()

    def get_payment_by_idempotency_key(self, idempotency_key: str) -> Payment | None:
        stmt = select(Payment).where(Payment.idempotency_key == idempotency_key)
        return self.session.scalars(stmt).first()

    def list_payments_for_org(self, org_id: uuid.UUID) -> Sequence[Payment]:
        stmt = select(Payment).where(Payment.org_id == org_id)
        return self.session.scalars(stmt).all()

    # --- Webhooks ---
    def log_webhook_event(self, event: WebhookEvent) -> WebhookEvent:
        self.session.add(event)
        self.session.flush()
        return event
