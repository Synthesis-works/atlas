/**
 * Regression tests: Billing page payments-list state synchronization.
 *
 * Production incident: after a successful PayPal capture, a single failed
 * GET /payments was silently swallowed, leaving "Recent payments" stale until
 * a manual browser reload. These tests pin the fix:
 *   1. the authoritative capture response is upserted optimistically,
 *   2. refresh failures are surfaced instead of swallowed,
 *   3. the list polls while a checkout awaits approval/capture,
 *   4. the PENDING row appears right after checkout creation.
 */

import type { ReactNode } from 'react';
import { useRef } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import BillingPage from '../pages/BillingPage';
import * as billingService from '../services/billingService';
import type { BillingProduct, PaymentRecord } from '../types';

const { capturedHandlers } = vi.hoisted(() => ({
  capturedHandlers: {
    onCreateOrder: null as (() => Promise<string>) | null,
    onApprove: null as (() => Promise<void>) | null,
    onCancel: null as (() => void) | null,
    onError: null as ((message: string) => void) | null,
  },
}));

vi.mock('@/features/billing/services/billingService', () => ({
  getPlans: vi.fn(),
  getPayments: vi.fn(),
  createCheckout: vi.fn(),
  capturePayment: vi.fn(),
  getPayment: vi.fn(),
}));

vi.mock('@/components/motion', () => ({
  ScrambleHeading: ({ children }: { children?: ReactNode }) => <h1>{children}</h1>,
}));

vi.mock('@/features/billing/components/PayPalCheckoutButton', () => {
  const PayPalCheckoutButton = (props: {
    currency: string;
    disabled?: boolean;
    onCreateOrder: () => Promise<string>;
    onApprove: () => Promise<void>;
    onCancel: () => void;
    onError: (message: string) => void;
  }) => {
    const handlersRef = useRef<typeof props | null>(null);
    if (handlersRef.current === null) {
      handlersRef.current = props;
      capturedHandlers.onCreateOrder = props.onCreateOrder;
      capturedHandlers.onApprove = props.onApprove;
      capturedHandlers.onCancel = props.onCancel;
      capturedHandlers.onError = props.onError;
    }
    return (
      <button type="button" data-testid="paypal-button" onClick={() => void props.onCreateOrder()}>
        PayPal
      </button>
    );
  };
  return { default: PayPalCheckoutButton };
});

const PLAN = {
  id: 'plan-plus-1',
  product_id: 'prod-1',
  name: 'Atlas Plus',
  amount: '9.00',
  currency: 'USD',
  billing_cycle: 'one_time' as const,
  provider_price_id: null,
  is_active: true,
};

const PRODUCT: BillingProduct = {
  id: 'prod-1',
  name: 'Credits',
  description: null,
  is_active: true,
  plans: [PLAN],
};

const PAYMENT_ID = '22222222-2222-4222-8222-222222222222';
const SESSION_ID = 'ORDER-SYNC-1';

const PENDING_RECORD: PaymentRecord = {
  id: PAYMENT_ID,
  org_id: 'org-1',
  amount: '9.00',
  currency: 'USD',
  status: 'pending',
  provider: 'paypal',
  provider_order_id: SESSION_ID,
  provider_payment_id: null,
  idempotency_key: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  capturedHandlers.onCreateOrder = null;
  capturedHandlers.onApprove = null;
  capturedHandlers.onCancel = null;
  capturedHandlers.onError = null;

  vi.mocked(billingService.getPlans).mockResolvedValue({ data: [PRODUCT], error: null });
  vi.mocked(billingService.getPayments).mockResolvedValue({ data: [], error: null });
  vi.mocked(billingService.createCheckout).mockResolvedValue({
    data: {
      session_id: SESSION_ID,
      url: 'https://paypal.example/approve',
      payment_id: PAYMENT_ID,
      provider: 'paypal',
    },
    error: null,
  });
  vi.mocked(billingService.capturePayment).mockResolvedValue({
    data: {
      payment_id: PAYMENT_ID,
      status: 'succeeded',
      capture_id: 'CAP-SYNC-1',
      provider_order_id: SESSION_ID,
      amount: '9.00',
      currency: 'USD',
    },
    error: null,
  });
});

afterEach(() => {
  vi.useRealTimers();
});

async function mountAndCreateOrder() {
  render(
    <MemoryRouter>
      <BillingPage />
    </MemoryRouter>
  );
  fireEvent.click(await screen.findByRole('button', { name: /atlas plus/i }));
  await waitFor(() => expect(capturedHandlers.onApprove).not.toBeNull());
  fireEvent.click(screen.getByTestId('paypal-button'));
  await waitFor(() => expect(billingService.createCheckout).toHaveBeenCalledTimes(1));
}

describe('BillingPage payments state synchronization', () => {
  it('shows the succeeded payment immediately even when every refresh fails', async () => {
    vi.mocked(billingService.getPayments).mockResolvedValue({
      data: [],
      error: 'network down',
    });

    await mountAndCreateOrder();
    await capturedHandlers.onApprove!();

    expect(await screen.findByText('Payment successful')).toBeTruthy();
    // Optimistic upsert from the capture response — no successful fetch needed.
    expect(screen.getByText(PAYMENT_ID)).toBeTruthy();
    expect(screen.getByText('succeeded')).toBeTruthy();
  });

  it('surfaces refresh failures instead of silently keeping a stale list', async () => {
    vi.mocked(billingService.getPayments).mockResolvedValue({
      data: [],
      error: 'HTTP Error 503',
    });

    await mountAndCreateOrder();
    await capturedHandlers.onApprove!();

    expect(
      await screen.findByText(/Could not refresh payments: HTTP Error 503/)
    ).toBeTruthy();
  });

  it('clears the error banner once a refresh succeeds', async () => {
    vi.mocked(billingService.getPayments)
      .mockResolvedValueOnce({ data: [], error: 'HTTP Error 503' })
      .mockResolvedValue({ data: [PENDING_RECORD], error: null });

    await mountAndCreateOrder();
    await capturedHandlers.onApprove!();

    expect(await screen.findByText(PAYMENT_ID)).toBeTruthy();
    await waitFor(() =>
      expect(screen.queryByText(/Could not refresh payments/)).toBeNull()
    );
  });

  it('surfaces the PENDING row right after checkout creation', async () => {
    vi.mocked(billingService.getPayments)
      .mockResolvedValueOnce({ data: [], error: null })
      .mockResolvedValue({ data: [PENDING_RECORD], error: null });

    await mountAndCreateOrder();

    expect(await screen.findByText(PAYMENT_ID)).toBeTruthy();
    expect(screen.getByText('pending')).toBeTruthy();
  });

  it('polls the payments list while awaiting approval', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      await mountAndCreateOrder();
      const callsAfterCheckout = vi.mocked(billingService.getPayments).mock.calls.length;

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      expect(
        vi.mocked(billingService.getPayments).mock.calls.length
      ).toBeGreaterThan(callsAfterCheckout);
    } finally {
      vi.useRealTimers();
    }
  });
});
