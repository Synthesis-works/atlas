/**
 * Billing — Service
 * Communicates with the backend /api/v1/billing endpoints via the generic
 * apiClient (JWT bearer injected automatically). The client never supplies
 * amounts: the backend derives them from the Atlas Price.
 */

import { apiClient } from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';
import type {
  BillingProduct,
  CaptureResult,
  CheckoutResult,
  PaymentProviderName,
  PaymentRecord,
} from '../types';

export async function getPlans(): Promise<ServiceResult<BillingProduct[]>> {
  try {
    const data = await apiClient.get<BillingProduct[]>('/api/v1/billing/plans');
    return { data, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to load plans' };
  }
}

export async function createCheckout(params: {
  plan_id: string;
  provider: PaymentProviderName;
  success_url: string;
  cancel_url: string;
  idempotency_key?: string;
}): Promise<ServiceResult<CheckoutResult>> {
  try {
    const data = await apiClient.post<CheckoutResult>('/api/v1/billing/checkout', params);
    return { data, error: null };
  } catch (err: any) {
    return { data: null as unknown as CheckoutResult, error: err?.message || 'Checkout failed' };
  }
}

export async function capturePayment(paymentId: string): Promise<ServiceResult<CaptureResult>> {
  try {
    const data = await apiClient.post<CaptureResult>(`/api/v1/billing/capture/${paymentId}`);
    return { data, error: null };
  } catch (err: any) {
    return { data: null as unknown as CaptureResult, error: err?.message || 'Capture failed' };
  }
}

export async function getPayments(): Promise<ServiceResult<PaymentRecord[]>> {
  try {
    const data = await apiClient.get<PaymentRecord[]>('/api/v1/billing/payments');
    return { data, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to load payments' };
  }
}

export async function getPayment(paymentId: string): Promise<ServiceResult<PaymentRecord>> {
  try {
    const data = await apiClient.get<PaymentRecord>(`/api/v1/billing/payments/${paymentId}`);
    return { data, error: null };
  } catch (err: any) {
    return { data: null as unknown as PaymentRecord, error: err?.message || 'Failed to load payment' };
  }
}