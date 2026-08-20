# PayPal Checkout Integration

This document describes how PayPal Checkout is integrated into Atlas as a
third payment provider (alongside Stripe and Razorpay) inside the existing
billing subsystem.

## Scope

- One-time purchases (credits) via PayPal Orders v2 (`intent=CAPTURE`).
- Server-side capture and reconciliation.
- Webhook processing (signature-verified) for completion/denial/refund events.
- Exactly-once credit activation backed by `credit_transactions`.

Subscriptions are **not** managed through PayPal: `PayPalGateway.cancel_subscription`
returns `False` (unsupported) and Atlas does not use PayPal Billing Agreements.

## Architecture

```
Frontend (BillingPage / PayPalCheckoutButton)
        |  POST /api/v1/billing/checkout        (auth token -> org)
        v
apps/backend/routers/billing.py
        |  BillingService.create_checkout_session
        v
services/billing/service.py
        |  GatewayRegistry.get_gateway(PaymentProvider.PAYPAL)
        v
services/billing/gateways/paypal_provider.py  ->  PayPal REST v2 (httpx)
                                                     /v1/oauth2/token
                                                     /v2/checkout/orders
                                                     /v2/checkout/orders/{id}/capture
                                                     /v1/notifications/verify-webhook-signature
```

The gateway is a third implementation of the existing `PaymentGateway` ABC.
No second billing subsystem was introduced; Stripe and Razorpay flows are
unchanged.

## Flow

1. **Checkout** — authenticated user picks a plan; `POST /checkout` derives
   amount/currency from the Atlas `Price` row (never from the client), creates
   a PayPal order, stores an Atlas `Payment` (status `created`,
   `provider_order_id` set, `idempotency_key` for idempotent re-entry).
2. **Approve** — the frontend redirects to PayPal; the buyer approves.
   Optional webhook `CHECKOUT.ORDER.APPROVED` moves the payment to `pending`.
3. **Capture** — the frontend calls `POST /capture/{payment_id}` after return.
   The server re-validates the provider-reported captured amount/currency
   against the Atlas payment; only then is the payment moved to `succeeded`
   and credits granted. A frontend callback alone grants nothing.
4. **Webhooks** — `POST /webhooks/paypal` verifies every event against the
   PayPal verification API (transmission headers + `PAYPAL_WEBHOOK_ID`) and
   processes `PAYMENT.CAPTURE.COMPLETED | DENIED | REFUNDED | REVERSED` and
   `CHECKOUT.ORDER.APPROVED`.
5. **Reconciliation** — `GET /payments/{payment_id}` re-fetches the order from
   PayPal and repairs local state when the provider reports completion that
   Atlas missed (e.g. a webhook delivered but not processed).

## Idempotency / exactly-once credits

- Webhook delivery is deduplicated by `(provider, provider_event_id)`.
- Re-submitting a checkout with the same `idempotency_key` returns the
  existing payment instead of creating a duplicate provider order.
- Credits are granted only to `succeeded` payments and only when no
  `credit_transactions` row with `reference_type='payment'` /
  `reference_id=<payment id>` exists. A partial unique index
  (`uq_credit_transactions_reference`) is the database-level guarantee, and
  activation runs inside a savepoint so a concurrent double-grant attempt
  cannot corrupt the payment transaction.

## Configuration

| Variable                  | Required | Default | Notes |
|---------------------------|----------|---------|-------|
| `PAYPAL_ENVIRONMENT`      | no       | `sandbox` | `sandbox` or `live` |
| `PAYPAL_CLIENT_ID`        | yes*     | —       | REST app client id |
| `PAYPAL_CLIENT_SECRET`    | yes*     | —       | Also honors legacy `PAYPAL_SECRET` |
| `PAYPAL_WEBHOOK_ID`       | for webhooks | — | Without it, webhook verification fails closed |
| `VITE_PAYPAL_CLIENT_ID`   | for UI   | —       | Public client id for the frontend SDK |

`*` Required when PayPal is used; `settings.paypal_enabled` is
`False` until both id and secret are set.

## API surface

- `GET /api/v1/billing/plans` — public plan catalog.
- `POST /api/v1/billing/checkout` — authenticated, tenant-scoped.
- `POST /api/v1/billing/capture/{payment_id}` — authenticated, tenant-scoped.
- `GET /api/v1/billing/payments` / `GET /api/v1/billing/payments/{payment_id}` —
  authenticated, tenant-scoped (the latter reconciles with PayPal).
- `POST /api/v1/billing/webhooks/paypal` — unauthenticated; authenticity via
  verified signature only.

All org-scoped routes derive the organization from the JWT claims, never from
the client.

## Database

Two migrations (both forward-only additive):

- `3f9c71a2e8b4` — adds `PAYPAL` to the `payment_provider` enum
  (irreversible per `docs/database/ENUM_POLICY.md`).
- `7d4a9c2f6e81` — partial unique index on `credit_transactions
  (reference_type, reference_id)`.

No new tables were added; the existing `payments` table already carried
`provider_order_id`, `provider_payment_id`, `metadata_json` and
`idempotency_key`.

## Tests

`services/billing/tests/` (added to pytest `testpaths` in `pyproject.toml`):

- `unit/test_paypal_gateway.py` — gateway behavior with `httpx.MockTransport`
  (OAuth caching, order creation, capture, reconciliation, webhook
  verification, refunds, network failures).
- `unit/test_billing_service_paypal.py` — idempotent checkout, server-side
  amount derivation, capture validation, ownership rules, credit activation.
- `unit/test_paypal_webhooks.py` — signature fail-closed, idempotent delivery,
  state transitions, no double-grant between capture and webhook paths.
- `api/test_billing_api.py` — auth enforcement, tenant isolation, amount
  tampering, plans endpoint, webhook endpoint.

Run:

```bash
uv run --extra dev pytest services/billing/tests -q
```

## Manual sandbox procedure

1. Set `PAYPAL_ENVIRONMENT=sandbox` plus sandbox REST app credentials
   (`PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`) and `VITE_PAYPAL_CLIENT_ID`
   in the environment (never commit them).
2. Run Postgres, Redis, backend, and the landing app locally.
3. Ensure at least one active `Price` exists in the database.
4. From the dashboard Billing page, choose a plan → PayPal checkout →
   approve with a sandbox buyer account (or `sb-buyer@paypal.com` test
   account) → return → capture is executed server-side.
5. Verify in the database: `payments.status='succeeded'`,
   `credit_accounts.balance` increased, exactly one matching
   `credit_transactions` row.
6. Reconcile: call `GET /payments/{payment_id}` and confirm no duplicate
   credits.
7. Webhooks: expose the backend via a tunnel (e.g. `ngrok`) and register
   `https://<tunnel>/api/v1/billing/webhooks/paypal` in the PayPal app
   dashboard with event subscriptions
   `PAYMENT.CAPTURE.COMPLETED`, `PAYMENT.CAPTURE.DENIED`,
   `PAYMENT.CAPTURE.REFUNDED`, `PAYMENT.CAPTURE.REVERSED`,
   `CHECKOUT.ORDER.APPROVED`. Set `PAYPAL_WEBHOOK_ID` to the webhook id shown
   in the dashboard, then send a test webhook and confirm the payment state
   changes without double-granting credits.

## Limitations

- No PayPal-native subscriptions (Atlas treats PayPal as one-time purchases).
- Refunds are full-capture refunds (the gateway contract carries no currency).
- `PAYPAL_WEBHOOK_ID` must be provisioned before webhook processing works;
  until then, webhook requests fail closed (HTTP 400).
- Live environment requires separate live REST app credentials and webhook
  registration.