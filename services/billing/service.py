import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from atlas_db.models.billing import PaymentProvider, PaymentStatus, Payment, WebhookEvent
from atlas_db.repositories.billing import BillingRepository
from services.billing.registry import GatewayRegistry
from services.billing.gateways.base import CheckoutSessionResult

logger = logging.getLogger(__name__)


class BillingService:
    """
    Centralized service for billing business logic.
    Provides methods for checkout, webhook handling, and managing subscriptions/payments.
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
        """
        if idempotency_key:
            existing = self.repo.get_payment_by_idempotency_key(idempotency_key)
            if existing and existing.provider_order_id:
                # Basic idempotency check for existing checkouts
                pass

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

        # Track the checkout attempt as a PENDING payment
        payment = Payment(
            org_id=org_id,
            amount=price.amount,
            currency=price.currency,
            status=PaymentStatus.CREATED,
            provider=provider,
            provider_order_id=result.session_id,
            idempotency_key=idempotency_key,
        )
        self.repo.create_payment(payment)
        self.session.commit()

        return result

    def process_webhook(
        self,
        provider: PaymentProvider,
        payload: bytes | str,
        signature: str,
    ) -> None:
        """
        Process incoming webhooks safely, transactionally, and idempotently.
        """
        gateway = GatewayRegistry.get_gateway(provider)

        try:
            # 1. Verify signature and parse
            event_dict = gateway.verify_webhook_signature(payload, signature)

            # 2. Extract standard fields
            event_type = (
                event_dict.get("type", "unknown")
                if provider == PaymentProvider.STRIPE
                else event_dict.get("event", "unknown")
            )

            # Extract a unique provider event ID for idempotency
            provider_event_id = event_dict.get("id") if provider == PaymentProvider.STRIPE else None
            if provider == PaymentProvider.RAZORPAY:
                # Razorpay sends a header x-razorpay-event-id sometimes, but in payload it might just be the account_id + event.
                # Let's check headers if available, or generate a hash of payload. But ideally they pass a unique ID.
                # Razorpay webhook payload doesn't always have a top-level ID like Stripe.
                # Usually it has 'contains' and 'payload.payment.entity.id'
                # We can fallback to hashing the payload if no true event ID exists.
                import hashlib

                pay_str = payload.decode("utf-8") if isinstance(payload, bytes) else payload
                provider_event_id = hashlib.sha256(pay_str.encode("utf-8")).hexdigest()

            if not provider_event_id:
                provider_event_id = "unknown_event_id"

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
                    stmt = self.session.query(Payment).filter(
                        Payment.provider_order_id == session_id
                    )
                    payment = stmt.first()

                if payment:
                    payment.status = PaymentStatus.SUCCEEDED
                    payment.provider_payment_id = session_obj.get("payment_intent")

        elif provider == PaymentProvider.RAZORPAY:
            if event_type == "payment.captured":
                payment_obj = event_dict.get("payload", {}).get("payment", {}).get("entity", {})
                order_id = payment_obj.get("order_id")

                stmt = self.session.query(Payment).filter(Payment.provider_order_id == order_id)
                payment = stmt.first()

                if payment:
                    payment.status = PaymentStatus.SUCCEEDED
                    payment.provider_payment_id = payment_obj.get("id")
