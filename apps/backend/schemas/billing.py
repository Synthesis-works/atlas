import uuid
from decimal import Decimal
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field

from atlas_db.models.billing import PaymentProvider, PaymentStatus, SubscriptionStatus, InvoiceStatus, BillingCycle


class CheckoutRequest(BaseModel):
    plan_id: uuid.UUID = Field(..., description="The ID of the Price/Plan to checkout")
    provider: PaymentProvider = Field(..., description="The payment gateway to use (stripe or razorpay)")
    success_url: str = Field(..., description="URL to redirect to after successful payment")
    cancel_url: str = Field(..., description="URL to redirect to if payment is cancelled")
    idempotency_key: Optional[str] = Field(None, description="Unique key for idempotency")


class CheckoutResponse(BaseModel):
    session_id: str
    url: str


class PlanResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    name: Optional[str]
    amount: Decimal
    currency: str
    billing_cycle: BillingCycle
    provider_price_id: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    is_active: bool
    plans: List[PlanResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
        

class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    price_id: uuid.UUID
    status: SubscriptionStatus
    provider: Optional[PaymentProvider]
    started_at: datetime
    expires_at: Optional[datetime]
    canceled_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    subscription_id: Optional[uuid.UUID]
    amount: Decimal
    currency: str
    status: InvoiceStatus
    issued_at: datetime
    
    class Config:
        from_attributes = True


class PaymentResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    amount: Decimal
    currency: str
    status: PaymentStatus
    provider: PaymentProvider
    
    class Config:
        from_attributes = True
