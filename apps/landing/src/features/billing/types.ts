/**
 * Billing — Domain Types
 * Mirrors apps/backend/schemas/billing.py response shapes.
 */

export type BillingCycle = 'one_time' | 'monthly' | 'yearly';
export type PaymentProviderName = 'stripe' | 'razorpay' | 'paypal' | 'manual';

export interface PricePlan {
  id: string;
  product_id: string;
  name: string | null;
  amount: string;
  currency: string;
  billing_cycle: BillingCycle;
  provider_price_id: string | null;
  is_active: boolean;
}

export interface BillingProduct {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  plans: PricePlan[];
}

export interface CheckoutResult {
  session_id: string;
  url: string;
  payment_id: string | null;
  provider: PaymentProviderName | null;
}

export interface CaptureResult {
  payment_id: string;
  status: string;
  capture_id: string | null;
  provider_order_id: string | null;
  amount: string | null;
  currency: string | null;
}

export interface PaymentRecord {
  id: string;
  org_id: string;
  amount: string;
  currency: string;
  status: string;
  provider: PaymentProviderName;
  provider_order_id: string | null;
  provider_payment_id: string | null;
  idempotency_key: string | null;
}

export type CheckoutPhase =
  | 'idle'
  | 'creating'
  | 'approving'
  | 'capturing'
  | 'success'
  | 'cancel'
  | 'failure';