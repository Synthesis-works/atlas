import hashlib
import logging
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from atlas_db.models.billing import (
    CreditAccount,
    CreditTransaction,
    CreditTransactionType,
    Payment,
    PaymentProvider,
    PaymentStatus,
    WebhookEvent,
)
from atlas_db.repositories.billing import BillingRepository
from services.billing.registry import GatewayRegistry
from services.billing.gateways.base import CaptureResult, CheckoutSessionResult

logger = logging.getLogger(__name__)


class BillingService:
    """
    Centralized service for billing business logic.
    Provides methods for checkout, capture, reconciliation, webhook handling,
    and credit/entitlement activation. Payment provider details are hidden
    behind the ``PaymentGateway`` interface.
    """

    def __init__(self, session: Session):
        self.session = session
        self.repo = BillingRepository(session)

    def create_checkout_session(
        self,
        org_id: uuid.UUID,
        price_id: uuid.UUID,
        provider: PaymentProvider,
        success_url: str,
        cancel_url: str,
        idempotency_key: str | None = None,
    ) -> CheckoutSessionResult:
        """
        Initiates a checkout session for a specific price.

        The amount and currency are always derived from the Atlas ``Price`` row,
        never from the client. When an ``idempotency_key`` already produced a
        valid payment, the existing checkout is returned instead of creating a
        second provider order.
        """
        if idempotency_key:
            existing = self.repo.get_payment_by_idempotency_key(idempotency_key)
            if existing and existing.provider_order_id:
                metadata = existing.metadata_json or {}
                return CheckoutSessionResult(
                    session_id=existing.provider_order_id,
                    url=metadata.get("approve_url", ""),
                )

        price = self.repo.get_price(price_id)
        if not price:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price not found")

        if not price.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Price is no longer active"
            )

        gateway = GatewayRegistry.get_gateway(provider)

        gateway_price_id = price.provider_price_id or str(price.id)

        result = gateway.create_checkout_session(
            price_id=gateway_price_id,
            org_id=org_id,
            amount=price.amount,
            currency=price.currency,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        payment = Payment(
            org_id=org_id,
            amount=price.amount,
            currency=price.currency,
            status=PaymentStatus.CREATED,
            provider=provider,
            provider_order_id=result.session_id,
            idempotency_key=idempotency_key,
        )
        if provider == PaymentProvider.PAYPAL:
            payment.metadata_json = {
                "approve_url": result.url,
                "provider_order_id": result.session_id,
            }
        self.repo.create_payment(payment)
        self.session.commit()

        return result

    def capture_payment(self, org_id: uuid.UUID, payment_id: uuid.UUID) -> CaptureResult:
        """
        Capture an approved PayPal order server-side.

        - Ownership is enforced against ``org_id`` (resolved from auth claims).
        - The captured amount/currency returned by the provider is validated
          against the Atlas payment before any state transition.
        - Credits/entitlements are activated exactly once (idempotent).
        - A frontend callback alone never grants anything: capture must succeed
          and be re-validated against the provider's authoritative response.
        """
        payment = self.repo.get_payment(payment_id)
        if not payment or payment.org_id != org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

        if payment.provider != PaymentProvider.PAYPAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Capture is only supported for PayPal payments",
            )

        if payment.status in (PaymentStatus.SUCCEEDED, PaymentStatus.FAILED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Payment is already in state {payment.status.value}",
            )

        if not payment.provider_order_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Payment has no provider order"
            )

        gateway = GatewayRegistry.get_gateway(PaymentProvider.PAYPAL)
        result = gateway.capture_payment(
            payment.provider_order_id, payment.amount, payment.currency
        )

        # Re-validate the provider's authoritative captured amount/currency.
        if result.amount is not None and result.amount != payment.amount:
            logger.warning(
                "PayPal capture amount mismatch for payment %s: expected %s got %s",
                payment.id,
                payment.amount,
                result.amount,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Captured amount does not match the Atlas payment",
            )
        if result.currency and result.currency != payment.currency:
            logger.warning(
                "PayPal capture currency mismatch for payment %s: expected %s got %s",
                payment.id,
                payment.currency,
                result.currency,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Captured currency does not match the Atlas payment",
            )

        payment.provider_payment_id = result.capture_id
        metadata = dict(payment.metadata_json or {})
        metadata["capture_id"] = result.capture_id
        metadata["capture_status"] = result.status
        payment.metadata_json = metadata

        if result.status.upper() == "COMPLETED":
            payment.status = PaymentStatus.SUCCEEDED
            self._activate_credits_safely(payment)
        else:
            payment.status = PaymentStatus.FAILED

        self.session.commit()
        return result

    def get_payment_status(self, org_id: uuid.UUID, payment_id: uuid.UUID) -> Payment:
        """
        Reconcile a payment against the provider's authoritative state.

        For PayPal the order is re-fetched and the local state is repaired when
        the provider reports completion that Atlas has not yet recorded (e.g. a
        webhook that was delivered but not processed). Idempotent: activation
        is guarded by payment state and the credit-transaction reference.
        """
        payment = self.repo.get_payment(payment_id)
        if not payment or payment.org_id != org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

        if payment.provider == PaymentProvider.PAYPAL and payment.provider_order_id:
            gateway = GatewayRegistry.get_gateway(PaymentProvider.PAYPAL)
            order = gateway.get_payment(payment.provider_order_id)

            purchase_units = order.get("purchase_units") or []
            if purchase_units:
                amount = purchase_units[0].get("amount") or {}
                provider_value = amount.get("value")
                provider_currency = amount.get("currency_code")
                if provider_value and Decimal(provider_value) != payment.amount:
                    logger.warning("PayPal order amount mismatch for payment %s", payment.id)
                if provider_currency and provider_currency != payment.currency:
                    logger.warning("PayPal order currency mismatch for payment %s", payment.id)

            order_status = str(order.get("status", "")).upper()
            if order_status == "COMPLETED" and payment.status not in (
                PaymentStatus.SUCCEEDED,
                PaymentStatus.REFUNDED,
            ):
                payment.status = PaymentStatus.SUCCEEDED
                purchase_units = order.get("purchase_units") or []
                if purchase_units:
                    captures = purchase_units[0].get("payments", {}).get("captures") or []
                    if captures:
                        payment.provider_payment_id = (
                            captures[0].get("id") or payment.provider_payment_id
                        )
                self._activate_credits_safely(payment)
                self.session.commit()
            elif order_status in ("VOIDED", "CANCELED", "FAILED", "EXPIRED") and payment.status in (
                PaymentStatus.CREATED,
                PaymentStatus.PENDING,
            ):
                payment.status = PaymentStatus.FAILED
                self.session.commit()

        return payment

    # ------------------------------------------------------------- webhooks

    def process_webhook(
        self,
        provider: PaymentProvider,
        payload: bytes | str,
        signature: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        Process incoming webhooks safely, transactionally, and idempotently.
        """
        gateway = GatewayRegistry.get_gateway(provider)

        try:
            # 1. Verify signature and parse
            event_dict = gateway.verify_webhook_signature(payload, signature, headers)

            # 2. Extract standard fields per provider
            event_type, provider_event_id = self._extract_event_identity(
                provider, event_dict, payload
            )

            # 3. Check for Idempotency (Already processed?)
            existing_event = (
                self.session.query(WebhookEvent)
                .filter_by(provider=provider, provider_event_id=provider_event_id)
                .first()
            )

            if existing_event:
                logger.info(f"Webhook event already processed: {provider} - {provider_event_id}")
                return  # Idempotent return

            # 4. Store event as unprocessed
            event_record = WebhookEvent(
                provider=provider,
                provider_event_id=provider_event_id,
                event_type=event_type,
                payload=event_dict,
                processed=False,
            )
            self.repo.log_webhook_event(event_record)

            # 5. Handle business logic atomically
            with self.session.begin_nested():
                self._handle_event(provider, event_type, event_dict)
                event_record.processed = True

            # 6. Commit transaction
            self.session.commit()

        except IntegrityError:
            self.session.rollback()
            logger.info("Webhook event likely processed concurrently.")
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            self.session.rollback()
            raise

    def _extract_event_identity(
        self, provider: PaymentProvider, event_dict: dict[str, Any], payload: bytes | str
    ) -> tuple[str, str]:
        """
        Return ``(event_type, provider_event_id)`` per provider convention.
        """
        if provider == PaymentProvider.STRIPE:
            return (
                event_dict.get("type", "unknown"),
                event_dict.get("id") or "unknown_event_id",
            )
        if provider == PaymentProvider.RAZORPAY:
            pay_str = payload.decode("utf-8") if isinstance(payload, bytes) else payload
            return (
                event_dict.get("event", "unknown"),
                hashlib.sha256(pay_str.encode("utf-8")).hexdigest(),
            )
        if provider == PaymentProvider.PAYPAL:
            return (
                event_dict.get("event_type", "unknown"),
                event_dict.get("id") or "unknown_event_id",
            )
        return ("unknown", "unknown_event_id")

    def _handle_event(
        self, provider: PaymentProvider, event_type: str, event_dict: dict[str, Any]
    ) -> None:
        """
        Handle the core business logic for the event types.
        """
        if provider == PaymentProvider.STRIPE:
            if event_type == "checkout.session.completed":
                session_obj = event_dict.get("data", {}).get("object", {})
                session_id = session_obj.get("id")

                payment = self.repo.get_payment_by_provider_id(session_id)
                if not payment:
                    payment = self.repo.get_payment_by_provider_order_id(session_id)

                if payment:
                    payment.status = PaymentStatus.SUCCEEDED
                    payment.provider_payment_id = session_obj.get("payment_intent")

        elif provider == PaymentProvider.RAZORPAY:
            if event_type == "payment.captured":
                payment_obj = event_dict.get("payload", {}).get("payment", {}).get("entity", {})
                order_id = payment_obj.get("order_id")

                payment = self.repo.get_payment_by_provider_order_id(order_id)

                if payment:
                    payment.status = PaymentStatus.SUCCEEDED
                    payment.provider_payment_id = payment_obj.get("id")

        elif provider == PaymentProvider.PAYPAL:
            resource = event_dict.get("resource", {}) or {}
            payment = self._find_payment_for_paypal_resource(resource, event_type)

            if not payment:
                logger.info("PayPal webhook %s referenced an unknown payment", event_type)
                return

            if event_type == "PAYMENT.CAPTURE.COMPLETED":
                payment.status = PaymentStatus.SUCCEEDED
                payment.provider_payment_id = resource.get("id") or payment.provider_payment_id
                metadata = dict(payment.metadata_json or {})
                metadata["capture_id"] = resource.get("id")
                metadata["capture_status"] = resource.get("status")
                payment.metadata_json = metadata
                self._activate_credits_for_payment(payment)
            elif event_type == "PAYMENT.CAPTURE.DENIED":
                payment.status = PaymentStatus.FAILED
            elif event_type in ("PAYMENT.CAPTURE.REFUNDED", "PAYMENT.CAPTURE.REVERSED"):
                payment.status = PaymentStatus.REFUNDED
            elif event_type == "CHECKOUT.ORDER.APPROVED":
                payment.status = PaymentStatus.PENDING

    def _find_payment_for_paypal_resource(
        self, resource: dict[str, Any], event_type: str = ""
    ) -> Payment | None:
        """Locate the Atlas payment referenced by a PayPal webhook resource."""
        capture_id = resource.get("id")
        if capture_id:
            payment = self.repo.get_payment_by_provider_id(capture_id)
            if payment:
                return payment

        order_id = resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
        if not order_id:
            order_id = resource.get("order_id")
        if not order_id and event_type.startswith("CHECKOUT.ORDER."):
            # ORDER-type events carry the order id directly in resource.id.
            order_id = resource.get("id")
        if order_id:
            payment = self.repo.get_payment_by_provider_order_id(order_id)
            if payment:
                return payment
        return None

    # -------------------------------------------------------- entitlements

    def _activate_credits_safely(self, payment: Payment) -> None:
        """
        Activate credits inside a savepoint so a concurrent double-grant attempt
        (unique index violation) reverts only the savepoint and leaves the
        payment transaction intact.
        """
        try:
            with self.session.begin_nested():
                self._activate_credits_for_payment(payment)
        except IntegrityError:
            logger.info("Credits already granted for payment %s; skipping", payment.id)

    def _activate_credits_for_payment(self, payment: Payment) -> None:
        """
        Grant the org's credit balance for a successful payment, exactly once.

        Idempotency chain:
        1. Only SUCCEEDED payments are eligible (state-transition guard).
        2. A ``CreditTransaction`` with ``reference_type="payment"`` and
           ``reference_id=<payment id>`` must already exist -> skip.
        3. The partial unique index on ``(reference_type, reference_id)`` is the
           database-level guarantee against concurrent double-grants.
        """
        if payment.status != PaymentStatus.SUCCEEDED:
            return

        account = self.repo.get_credit_account(payment.org_id)
        if account is None:
            account = CreditAccount(org_id=payment.org_id, balance=Decimal("0"))
            self.repo.create_credit_account(account)

        reference_id = str(payment.id)
        if self.repo.get_credit_transaction_by_reference("payment", reference_id):
            logger.info("Credits already granted for payment %s", payment.id)
            return

        account.balance += payment.amount
        transaction = CreditTransaction(
            account_id=account.id,
            amount=payment.amount,
            transaction_type=CreditTransactionType.PURCHASE,
            reference_type="payment",
            reference_id=reference_id,
            description=f"Credits purchased via {payment.provider.value} payment {payment.id}",
        )
        self.session.add(transaction)
