/**
 * Billing — Workspace Billing Page
 *
 * Lists Atlas plans and drives a PayPal Checkout flow:
 *   plan -> POST /billing/checkout -> PayPal approval -> POST /billing/capture
 *
 * The backend derives the amount server-side from the Price; the page never
 * sends a price to the API.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { pageCrossfade } from '@/lib/motion';
import { Badge, Card } from '@/design/primitives';
import { ScrambleHeading } from '@/components/motion';
import {
  CheckCircle2,
  CreditCard,
  RefreshCw,
  ShieldCheck,
  XCircle,
  type LucideIcon,
} from 'lucide-react';
import PayPalCheckoutButton from '@/features/billing/components/PayPalCheckoutButton';
import {
  capturePayment,
  createCheckout,
  getPayment,
  getPayments,
  getPlans,
} from '@/features/billing/services/billingService';
import type { BillingProduct, CheckoutPhase, PaymentRecord, PricePlan } from '@/features/billing/types';

const PHASE_COPY: Record<CheckoutPhase, { title: string; detail: string }> = {
  idle: { title: 'Choose a plan to begin', detail: 'Payment is processed securely by PayPal.' },
  creating: { title: 'Creating checkout', detail: 'Contacting Atlas billing…' },
  approving: { title: 'Waiting for approval', detail: 'Complete the payment in the PayPal window.' },
  capturing: { title: 'Capturing payment', detail: 'Atlas is verifying and capturing the payment…' },
  success: { title: 'Payment successful', detail: 'Your credits have been activated.' },
  cancel: { title: 'Payment cancelled', detail: 'No charge was made. You can try again.' },
  failure: { title: 'Payment failed', detail: 'The payment could not be completed.' },
};

function formatAmount(amount: string, currency: string): string {
  const num = Number(amount);
  if (Number.isNaN(num)) return `${amount} ${currency}`;
  return `${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
}

const STATUS_STYLE: Record<string, string> = {
  succeeded: 'text-emerald-400 border-emerald-400/25 bg-emerald-400/10',
  pending: 'text-amber-300 border-amber-300/25 bg-amber-300/10',
  created: 'text-sky-300 border-sky-300/25 bg-sky-300/10',
  failed: 'text-red-400 border-red-400/25 bg-red-400/10',
  cancelled: 'text-white/50 border-white/10 bg-white/5',
  refunded: 'text-white/50 border-white/10 bg-white/5',
};

export default function BillingPage() {
  const [products, setProducts] = useState<BillingProduct[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<PricePlan | null>(null);
  const [phase, setPhase] = useState<CheckoutPhase>('idle');
  const [phaseDetail, setPhaseDetail] = useState<string | null>(null);
  /**
   * The PayPal SDK button binds its onApprove handler once at mount time, so a
   * state-based closure would observe a stale (null) payment id. Read the id
   * from a ref instead: the ref is updated when the checkout API responds and
   * is always readable by whichever closure instance the SDK invokes.
   */
  const paymentIdRef = useRef<string | null>(null);
  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [reconciling, setReconciling] = useState<string | null>(null);

  const refreshPlans = useCallback(async () => {
    const result = await getPlans();
    if (result.error) {
      setLoadError(result.error);
      setProducts([]);
    } else {
      setProducts(result.data);
      setLoadError(null);
    }
  }, []);

  const refreshPayments = useCallback(async () => {
    const result = await getPayments();
    if (!result.error) setPayments(result.data);
  }, []);

  useEffect(() => {
    void refreshPlans();
    void refreshPayments();
  }, [refreshPlans, refreshPayments]);

  const handleCreateOrder = useCallback(async (): Promise<string> => {
    if (!selectedPlan) throw new Error('No plan selected');
    setPhase('creating');
    setPhaseDetail(null);
    const result = await createCheckout({
      plan_id: selectedPlan.id,
      provider: 'paypal',
      success_url: `${window.location.origin}/dashboard/billing?status=success`,
      cancel_url: `${window.location.origin}/dashboard/billing?status=cancel`,
      idempotency_key: `paypal-${selectedPlan.id}-${Date.now()}`,
    });
    if (result.error || !result.data) {
      setPhase('failure');
      setPhaseDetail(result.error || 'Checkout could not be created');
      throw new Error(result.error || 'Checkout could not be created');
    }
    paymentIdRef.current = result.data.payment_id;
    setPhase('approving');
    return result.data.session_id;
  }, [selectedPlan]);

  const handleApprove = useCallback(async () => {
    const paymentId = paymentIdRef.current;
    if (!paymentId) {
      setPhase('failure');
      setPhaseDetail('No payment reference available');
      return;
    }
    setPhase('capturing');
    setPhaseDetail(null);
    const result = await capturePayment(paymentId);
    if (result.error || !result.data) {
      setPhase('failure');
      setPhaseDetail(result.error || 'Capture failed');
      return;
    }
    if (result.data.status === 'succeeded') {
      setPhase('success');
      await refreshPayments();
    } else {
      setPhase('failure');
      setPhaseDetail(`Payment ended in state: ${result.data.status}`);
    }
  }, [refreshPayments]);

  const handleCancel = useCallback(() => {
    setPhase('cancel');
  }, []);

  const handleError = useCallback((message: string) => {
    setPhase('failure');
    setPhaseDetail(message);
  }, []);

  const handleReconcile = useCallback(
    async (payment: PaymentRecord) => {
      setReconciling(payment.id);
      const result = await getPayment(payment.id);
      setReconciling(null);
      if (!result.error) {
        await refreshPayments();
      }
    },
    [refreshPayments]
  );

  const activePlans = useMemo(
    () => products.flatMap((p) => p.plans.filter((plan) => plan.is_active)),
    [products]
  );

  const phaseCopy = PHASE_COPY[phase];
  const PhaseIcon: LucideIcon =
    phase === 'success' ? CheckCircle2 : phase === 'failure' || phase === 'cancel' ? XCircle : CreditCard;

  return (
    <motion.div
      variants={pageCrossfade}
      initial="initial"
      animate="animate"
      exit="exit"
      className="p-4 sm:p-6 lg:p-7 max-w-[1440px] mx-auto w-full space-y-6"
    >
      <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-white/35">
            <CreditCard className="h-3.5 w-3.5 text-accent/80" />
            Billing
          </div>
          <ScrambleHeading text="Billing" className="mt-2 text-2xl font-semibold tracking-tight text-white" />
          <p className="mt-1 text-sm text-white/40">
            Purchase credits for your workspace. Amounts are set by Atlas — never by the browser.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            void refreshPlans();
            void refreshPayments();
          }}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-accent/30 bg-accent/10 px-3.5 py-2 text-xs font-medium text-accent-hover transition-colors hover:bg-accent/20"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </header>

      {loadError && (
        <div className="rounded-lg border border-red-500/25 bg-red-500/5 px-4 py-3 text-sm text-red-300">
          {loadError}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {activePlans.map((plan) => {
          const product = products.find((p) => p.plans.some((pl) => pl.id === plan.id));
          const selected = selectedPlan?.id === plan.id;
          return (
            <button
              key={plan.id}
              type="button"
              onClick={() => {
                setSelectedPlan(plan);
                setPhase('idle');
                setPhaseDetail(null);
                paymentIdRef.current = null;
              }}
              className={`text-left rounded-xl border p-5 transition-colors ${
                selected
                  ? 'border-accent/50 bg-accent/10'
                  : 'border-white/[0.08] bg-white/[0.02] hover:border-white/20'
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-white/80">{plan.name || product?.name || 'Plan'}</p>
                <Badge variant="outline" className="!px-2.5 !py-0.5 !text-[10px]">
                  {plan.billing_cycle}
                </Badge>
              </div>
              <p className="mt-3 text-2xl font-semibold tracking-tight text-white tabular-nums">
                {formatAmount(plan.amount, plan.currency)}
              </p>
              <p className="mt-1 text-[11px] text-white/30">{product?.description || product?.name}</p>
            </button>
          );
        })}
        {activePlans.length === 0 && !loadError && (
          <Card className="!rounded-lg !p-5 col-span-full">
            <p className="text-sm text-white/50">No active plans are published yet.</p>
          </Card>
        )}
      </div>

      {selectedPlan && (
        <Card className="!rounded-lg !p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-white/35">
                <PhaseIcon className="h-3.5 w-3.5 text-accent/80" />
                Checkout
              </div>
              <p className="mt-2 text-sm font-medium text-white">{phaseCopy.title}</p>
              <p className="mt-0.5 text-xs text-white/30">
                {phaseDetail || phaseCopy.detail}
              </p>
            </div>
            <Badge variant="outline" className="shrink-0 !px-2.5 !py-0.5 !text-[10px]">
              {formatAmount(selectedPlan.amount, selectedPlan.currency)}
            </Badge>
          </div>

          {phase !== 'success' && phase !== 'cancel' && (
            <div className="mt-5">
              <PayPalCheckoutButton
                key={selectedPlan.id}
                currency={selectedPlan.currency}
                disabled={phase === 'creating' || phase === 'capturing'}
                onCreateOrder={handleCreateOrder}
                onApprove={handleApprove}
                onCancel={handleCancel}
                onError={handleError}
              />
            </div>
          )}

          <div className="mt-5 flex items-center gap-2 text-[11px] text-white/30">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400/70" />
            Payments are captured and verified by the Atlas server. Credits activate only after a verified capture.
          </div>
        </Card>
      )}

      <div className="space-y-3">
        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-white/35">
          Recent payments
        </div>
        {payments.length === 0 && (
          <Card className="!rounded-lg !p-5">
            <p className="text-sm text-white/50">No payments yet.</p>
          </Card>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {payments.map((payment) => (
            <Card key={payment.id} className="!rounded-lg !p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm text-white/80 truncate">
                    {formatAmount(payment.amount, payment.currency)}
                  </p>
                  <p className="mt-0.5 text-[11px] text-white/30 truncate font-mono">{payment.id}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge
                    variant="outline"
                    className={`!px-2.5 !py-0.5 !text-[10px] ${STATUS_STYLE[payment.status] || ''}`}
                  >
                    {payment.status}
                  </Badge>
                  <button
                    type="button"
                    onClick={() => void handleReconcile(payment)}
                    disabled={reconciling === payment.id}
                    aria-label="Reconcile payment"
                    className="p-1.5 text-white/35 hover:text-white transition-colors disabled:opacity-40"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${reconciling === payment.id ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </motion.div>
  );
}