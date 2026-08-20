/**
 * Billing — PayPal Checkout Button
 *
 * Renders the official PayPal JS SDK Buttons. The SDK only ever receives the
 * public client id (VITE_PAYPAL_CLIENT_ID). Order creation and capture are
 * delegated to the Atlas backend — this component never touches privileged
 * PayPal APIs and never knows the Client Secret.
 */

import { useEffect, useRef, useState } from 'react';

declare global {
  interface Window {
    paypal?: any;
  }
}

export const PAYPAL_CLIENT_ID: string =
  (import.meta.env.VITE_PAYPAL_CLIENT_ID as string | undefined) || '';

const sdkCache = new Map<string, Promise<any>>();

function loadPayPalSdk(clientId: string, currency: string): Promise<any> {
  const key = `${clientId}|${currency}`;
  if (!sdkCache.has(key)) {
    sdkCache.set(
      key,
      new Promise((resolve, reject) => {
        const existing = document.querySelector<HTMLScriptElement>(
          `script[data-paypal-sdk="${clientId}"]`
        );
        if (existing) {
          existing.addEventListener('load', () => resolve(window.paypal));
          existing.addEventListener('error', () => reject(new Error('PayPal SDK failed to load')));
          return;
        }
        const script = document.createElement('script');
        script.src = `https://www.paypal.com/sdk/js?client-id=${clientId}&intent=capture&currency=${currency}&components=buttons`;
        script.async = true;
        script.dataset.paypalSdk = clientId;
        script.onload = () => resolve(window.paypal);
        script.onerror = () => reject(new Error('Failed to load PayPal SDK'));
        document.body.appendChild(script);
      })
    );
  }
  return sdkCache.get(key)!;
}

interface PayPalCheckoutButtonProps {
  currency: string;
  disabled?: boolean;
  onCreateOrder: () => Promise<string>;
  onApprove: () => Promise<void>;
  onCancel: () => void;
  onError: (message: string) => void;
}

export default function PayPalCheckoutButton({
  currency,
  disabled,
  onCreateOrder,
  onApprove,
  onCancel,
  onError,
}: PayPalCheckoutButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [sdkError, setSdkError] = useState<string | null>(null);
  const renderedRef = useRef(false);

  useEffect(() => {
    if (disabled) return;
    if (!PAYPAL_CLIENT_ID) {
      setSdkError('PayPal is not configured. Set VITE_PAYPAL_CLIENT_ID and reload.');
      return;
    }
    if (!containerRef.current || renderedRef.current) return;

    let cancelled = false;

    loadPayPalSdk(PAYPAL_CLIENT_ID, currency)
      .then((paypal) => {
        if (cancelled || !containerRef.current) return;
        paypal
          .Buttons({
            style: { layout: 'vertical', shape: 'rect', color: 'gold' },
            createOrder: () => onCreateOrder(),
            onApprove: async () => {
              await onApprove();
            },
            onCancel: () => onCancel(),
            onError: (err: any) => onError(err?.message || 'PayPal payment failed'),
          })
          .render(containerRef.current);
        renderedRef.current = true;
      })
      .catch((err: any) => {
        if (!cancelled) setSdkError(err?.message || 'Failed to load PayPal SDK');
      });

    return () => {
      cancelled = true;
    };
  }, [disabled, currency, onCreateOrder, onApprove, onCancel, onError]);

  if (sdkError) {
    return (
      <div className="rounded-lg border border-red-500/25 bg-red-500/5 px-3 py-2.5 text-xs text-red-300">
        {sdkError}
      </div>
    );
  }

  return <div ref={containerRef} className="paypal-buttons-container min-h-[45px]" />;
}