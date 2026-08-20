/**
 * Regression test: PayPal onApprove stale-closure bug.
 *
 * The PayPal SDK button binds its onApprove handler exactly once at mount
 * time. When approval arrives later, the SDK invokes the mount-time callback
 * — a closure that predates the checkout response. The fix routes the payment
 * id through a ref (`paymentIdRef.current`) instead of React state, so the
 * mount-time callback always observes the id assigned during createOrder.
 *
 * The PayPalCheckoutButton module is replaced by a test double that mirrors
 * the real SDK's "bind once per mount" behaviour: the handler captured at
 * mount time is the one invoked after createOrder completes, reproducing the
 * exact stale-callback scenario that broke production.
 */

import type { ReactNode } from 'react';
import { useRef } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import BillingPage from '../pages/BillingPage';
import * as billingService from '../services/billingService';
import type { BillingProduct } from '../types';

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

// The scramble heading uses IntersectionObserver/animation machinery that is
// irrelevant to this regression; render it as a plain heading.
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
    // Mirror the real SDK: handlers are captured exactly once, on the first
    // render of the mounted button, and never rebound for its lifetime. A
    // remount (plan switch, via the key on the real component) recaptures.
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

const PAYMENT_ID = '11111111-1111-4111-8111-111111111111';
const SESSION_ID = 'ORDER-1';

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
      capture_id: 'CAP-1',
      provider_order_id: SESSION_ID,
      amount: '9.00',
      currency: 'USD',
    },
    error: null,
  });
});

async function mountButtonAndCreateOrder() {
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

describe('BillingPage PayPal capture closure', () => {
  it('invokes capture with the payment id assigned AFTER the button mounted', async () => {
    await mountButtonAndCreateOrder();

    // The SDK would call the handler it bound at mount time — before the
    // checkout response set the payment id. The ref-based fix must make this
    // handler see the freshly assigned id.
    const mountTimeOnApprove = capturedHandlers.onApprove!;
    await mountTimeOnApprove();

    expect(billingService.capturePayment).toHaveBeenCalledTimes(1);
    expect(billingService.capturePayment).toHaveBeenCalledWith(PAYMENT_ID);
    expect(screen.queryByText('No payment reference available')).toBeNull();
    expect(await screen.findByText('Payment successful')).toBeTruthy();
  });

  it('fails with "No payment reference available" when checkout returns no payment id', async () => {
    vi.mocked(billingService.createCheckout).mockResolvedValue({
      data: {
        session_id: SESSION_ID,
        url: 'https://paypal.example/approve',
        payment_id: null,
        provider: 'paypal',
      },
      error: null,
    });

    await mountButtonAndCreateOrder();

    await capturedHandlers.onApprove!();

    expect(billingService.capturePayment).not.toHaveBeenCalled();
    expect(await screen.findByText('No payment reference available')).toBeTruthy();
  });

  it('rebinds the button handlers when the selected plan changes', async () => {
    const planB = { ...PLAN, id: 'plan-pro-1', name: 'Atlas Pro', amount: '149.00' };
    vi.mocked(billingService.getPlans).mockResolvedValue({
      data: [{ ...PRODUCT, plans: [PLAN, planB] }],
      error: null,
    });

    render(
      <MemoryRouter>
        <BillingPage />
      </MemoryRouter>
    );
    fireEvent.click(await screen.findByRole('button', { name: /atlas plus/i }));
    await waitFor(() => expect(capturedHandlers.onApprove).not.toBeNull());

    const beforeSwitch = capturedHandlers.onCreateOrder;
    fireEvent.click(await screen.findByRole('button', { name: /atlas pro/i }));
    await waitFor(() => expect(capturedHandlers.onCreateOrder).not.toBe(beforeSwitch));

    fireEvent.click(screen.getByTestId('paypal-button'));
    await waitFor(() => expect(billingService.createCheckout).toHaveBeenCalledTimes(1));
    expect(billingService.createCheckout).toHaveBeenCalledWith(
      expect.objectContaining({ plan_id: 'plan-pro-1' })
    );
  });
});