import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from atlas_db.core.base import Base, BaseMixin, utcnow


class PaymentProvider(str, enum.Enum):
    STRIPE = "stripe"
    RAZORPAY = "razorpay"
    MANUAL = "manual"


class PaymentStatus(str, enum.Enum):
    CREATED = "created"
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    DISPUTED = "disputed"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class BillingCycle(str, enum.Enum):
    ONE_TIME = "one_time"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class CreditTransactionType(str, enum.Enum):
    GRANT = "grant"
    PURCHASE = "purchase"
    DEDUCTION = "deduction"
    REFUND = "refund"


class Product(Base, BaseMixin):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    prices: Mapped[list["Price"]] = relationship(
        "Price", back_populates="product", cascade="all, delete-orphan"
    )


class Price(Base, BaseMixin):
    __tablename__ = "prices"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        Enum(BillingCycle, name="billing_cycle"), nullable=False
    )
    provider_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="prices")
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="price"
    )
    features: Mapped[list["PriceFeature"]] = relationship(
        "PriceFeature", back_populates="price", cascade="all, delete-orphan"
    )


class Feature(Base, BaseMixin):
    __tablename__ = "features"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    prices: Mapped[list["PriceFeature"]] = relationship(
        "PriceFeature", back_populates="feature", cascade="all, delete-orphan"
    )


class PriceFeature(Base, BaseMixin):
    __tablename__ = "price_features"

    price_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feature_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("features.id", ondelete="CASCADE"), nullable=False, index=True
    )

    price: Mapped["Price"] = relationship("Price", back_populates="features")
    feature: Mapped["Feature"] = relationship("Feature", back_populates="prices")


class Subscription(Base, BaseMixin):
    __tablename__ = "subscriptions"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"), nullable=False
    )
    provider: Mapped[PaymentProvider | None] = mapped_column(
        Enum(PaymentProvider, name="payment_provider"), nullable=True
    )
    provider_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    price: Mapped["Price"] = relationship("Price", back_populates="subscriptions")
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="subscription")


class Invoice(Base, BaseMixin):
    __tablename__ = "invoices"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"), nullable=False
    )
    provider: Mapped[PaymentProvider | None] = mapped_column(
        Enum(PaymentProvider, name="payment_provider"), nullable=True
    )
    provider_invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    tax_region: Mapped[str | None] = mapped_column(String(50), nullable=True)

    subscription: Mapped["Subscription | None"] = relationship(
        "Subscription", back_populates="invoices"
    )
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="invoice")


class Payment(Base, BaseMixin):
    __tablename__ = "payments"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"), nullable=False
    )
    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, name="payment_provider"), nullable=False
    )
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider_order_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)

    invoice: Mapped["Invoice | None"] = relationship("Invoice", back_populates="payments")
    refunds: Mapped[list["Refund"]] = relationship("Refund", back_populates="payment")


class Refund(Base, BaseMixin):
    __tablename__ = "refunds"

    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"), nullable=False
    )
    provider_refund_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    payment: Mapped["Payment"] = relationship("Payment", back_populates="refunds")


class CreditAccount(Base, BaseMixin):
    __tablename__ = "credit_accounts"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)

    transactions: Mapped[list["CreditTransaction"]] = relationship(
        "CreditTransaction", back_populates="account"
    )


class CreditTransaction(Base, BaseMixin):
    __tablename__ = "credit_transactions"

    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("credit_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    transaction_type: Mapped[CreditTransactionType] = mapped_column(
        Enum(CreditTransactionType, name="credit_transaction_type"), nullable=False
    )
    reference_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    account: Mapped["CreditAccount"] = relationship("CreditAccount", back_populates="transactions")


class UsageRecord(Base, BaseMixin):
    __tablename__ = "usage_records"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class WebhookEvent(Base, BaseMixin):
    __tablename__ = "webhook_events"

    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_event_id", name="uq_webhook_event_provider_event_id"
        ),
    )

    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, name="payment_provider"), nullable=False
    )
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
