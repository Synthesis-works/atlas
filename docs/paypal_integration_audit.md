# Atlas PayPal Integration — Pre-Implementation Audit Report

**Branch:** `feature/paypal-payments` (created from `origin/main` @ `8284282cc55938229136491b63d41896b783140f`)

**Audit date:** 2026-08-20

**Status:** Audit complete. Implementation has NOT started (Phase 3 stop).

This report describes the **actual state of the repository** at the branch base. It is not a generic recommendation document. Every claim below was verified by reading the source on this branch. Nothing was modified.

---

# 1. Repository snapshot

| Item | Value |
|---|---|
| Current branch | `feature/paypal-payments` |
| Base branch | `origin/main` |
| Base SHA | `8284282cc55938229136491b63d41896b783140f` (merge of PR #43, "login-worker-warmup") |
| Working tree | clean |
| Repo | `https://github.com/Synthesis-works/atlas.git` |
| Language | Python 3.11+ (backend), TypeScript/React 19 (frontend) |
| Backend framework | FastAPI + SQLAlchemy 2.0 + Alembic + Celery/Redis + pydantic-settings |
| Dependency manager | `uv` / `uv.lock` (canonical), Poetry optional |
| Formatting/lint/type | `ruff` (line-length 100), `mypy` |
| Version | `0.9.0` (`pyproject.toml`) |
| Recent relevant history | Billing/gateway work merged from PR #25 (`integrate_stripe_razorpay_payments`) and PR #28 (`integration/pr28-agent-billing`) |

## Repository layout (monorepo-style)

- `apps/backend` — FastAPI entrypoint, routers, services, schemas, Celery workers, event bus.
- `apps/landing` — the real frontend: Vite 8 + React 19 + TypeScript SPA (Vercel `atlas-web`).
- `apps/web` — **dead Next.js stub** (no `package.json`). `apps/admin` — empty placeholder.
- `packages/database/atlas_db` — SQLAlchemy models, repositories, Alembic migrations (the `atlas_db` distribution).
- `packages/*` — foundational libraries (config, auth, execution_engine, evaluation_engine, llm, etc.).
- `services/*` — business domains (billing, auth, dataset, evaluation, execution, report, search, storage, ...).
- `docker/`, `infrastructure/`, `deploy/`, `.github/workflows/` — deployment/CI.

## Relevant framework facts for this work

- API routes use Pydantic schemas decoupled from ORM models; repositories abstract DB access; background work is routed through the Celery event bus (`apps/backend/events/`).
- `apps/backend/config.py` uses `pydantic-settings` reading `.env` (`SettingsConfigDict(env_file=".env")`); `.env` is gitignored.
- Alembic migrations live in `packages/database/alembic/versions/`. Two migrations exist: baseline `7537275102f0_initial_atlas_schema_baseline.py` (126 KB, all tables) and `81db55ad9a77_rls_default_deny_for_backend_only_tables.py`.

---

# 2. Existing payment/billing architecture

**A payment/billing domain ALREADY EXISTS and is merged into `main`.** It is scaffold-grade in the API layer but has a real domain model, a provider gateway abstraction, a repository, idempotent webhook processing, and a registry.

**PayPal must be added to this system, not built as a parallel one.**

| Question | Answer |
|---|---|
| Payment domain present? | **Yes.** `services/billing/` |
| Payment/Order/Transaction model? | **Yes.** `Product`, `Price`, `Subscription`, `Invoice`, `Payment`, `Refund`, `CreditAccount`, `CreditTransaction`, `UsageRecord`, `WebhookEvent` in `packages/database/atlas_db/models/billing.py` |
| Provider abstraction? | **Yes.** `PaymentGateway` ABC in `services/billing/gateways/base.py` + `GatewayRegistry` in `services/billing/registry.py` |
| Billing service? | **Yes.** `BillingService` in `services/billing/service.py` (`create_checkout_session`, `process_webhook`, `_handle_event`) |
| Credit/entitlement system? | **Models only.** `CreditAccount`/`CreditTransaction` exist and are migrated, but **no service code reads, writes, or activates them anywhere** in the repo. Entitlement activation logic must be written. |
| Webhook infrastructure? | **Partial.** `WebhookEvent` table + idempotent `process_webhook` in `BillingService`; two provider webhook routes exist (stripe, razorpay). No PayPal. |
| Event bus / domain events? | **Execution-scoped only.** `ExecutionEventBus` (`apps/backend/events/bus.py`, `celery_bus.py`) is used for execution lifecycle events. Billing is not wired to it today; webhook handling is synchronous in the router. |

## Key existing billing symbols

- `PaymentGateway` ABC (`services/billing/gateways/base.py`) — abstract methods: `create_checkout_session(price_id, org_id, amount, currency, success_url, cancel_url) -> CheckoutSessionResult`, `verify_webhook_signature(payload, signature) -> dict`, `cancel_subscription(subscription_id) -> bool`, `refund_payment(payment_id, amount) -> bool`. `CheckoutSessionResult(session_id, url)` is a pydantic model.
- `StripeGateway` (`services/billing/gateways/stripe_provider.py`) — uses `stripe.checkout.Session.create`, `stripe.Webhook.construct_event`.
- `RazorpayGateway` (`services/billing/gateways/razorpay_provider.py`) — uses `razorpay.Client`; returns `order["id"]` as `session_id` and `url=""` (frontend JS popup).
- `GatewayRegistry.get_gateway(provider)` (`services/billing/registry.py`) — currently branches on `STRIPE` / `RAZORPAY`, else `ValueError`. **Needs a `PAYPAL` branch.**
- `BillingService.create_checkout_session(...)` — loads `Price` by id, checks `is_active`, calls gateway, persists a `Payment` with `status=CREATED`, `provider`, `provider_order_id=result.session_id`, `idempotency_key`. It does **not** verify idempotency meaningfully (the early `get_payment_by_idempotency_key` block is a no-op stub).
- `BillingService.process_webhook(provider, payload, signature)` — verifies signature via gateway, derives a `provider_event_id`, checks `WebhookEvent` for `(provider, provider_event_id)` uniqueness, stores the event, then applies business logic in a `begin_nested()` block; `IntegrityError` is treated as concurrent-duplicate. This is a solid idempotency skeleton that PayPal can reuse as-is.
- `BillingService._handle_event(...)` — Stripe `checkout.session.completed` → marks Payment `SUCCEEDED`; Razorpay `payment.captured` → marks Payment `SUCCEEDED`. **No credit/entitlement grant happens here** (gap for PayPal to fill).

## PayPal absence

- `paypal` appears **nowhere** in the codebase (grep across all files).
- `PaymentProvider` enum (`models/billing.py:23-26`) = `STRIPE`, `RAZORPAY`, `MANUAL`. **No `PAYPAL`.**
- No PayPal config keys, no PayPal gateway, no PayPal webhook route, no PayPal frontend code.

---

# 3. Existing database schema

All billing tables are created in the **initial baseline migration** `7537275102f0_initial_atlas_schema_baseline.py` (already committed to `main`, immutable per repo migration policy). Models are in `packages/database/atlas_db/models/billing.py`. JSONB columns and named Postgres ENUMs are used, which the SQLite test shims compile to `JSON`/`VARCHAR`.

| Table | Model | Key fields (abridged) | Notes |
|---|---|---|---|
| `products` | `Product` | `name`, `description`, `is_active` | |
| `prices` | `Price` | `product_id→products`, `amount` (Numeric 10,2), `currency` (3), `billing_cycle` enum, `provider_price_id` (idx), `is_active` | Reused for PayPal: `provider_price_id` optional |
| `features` / `price_features` | `Feature` / `PriceFeature` | m2m link | |
| `subscriptions` | `Subscription` | `org_id→organizations`, `price_id→prices`, `status` enum, `provider` enum, `provider_subscription_id` (idx), `started_at`, `expires_at`, `canceled_at` | |
| `invoices` | `Invoice` | `org_id`, `subscription_id`, `amount`, `currency`, `status` enum, `provider`, `provider_invoice_id` (idx), tax fields | |
| `payments` | `Payment` | `org_id`, `invoice_id` (nullable), `amount`, `currency`, `status` enum, `provider` enum, `provider_payment_id` (idx), `provider_order_id` (idx), `provider_customer_id` (idx), `metadata_json` JSONB, `idempotency_key` (unique) | **Directly sufficient for PayPal Checkout orders** — no new columns required |
| `refunds` | `Refund` | `payment_id`, `amount`, `status`, `provider_refund_id` | |
| `credit_accounts` | `CreditAccount` | `org_id` (unique), `balance` Numeric 15,2 | Unused by any service code |
| `credit_transactions` | `CreditTransaction` | `account_id`, `amount`, `transaction_type` enum (GRANT/PURCHASE/DEDUCTION/REFUND), `reference_type`, `reference_id` (idx), `description` | Unused by any service code |
| `usage_records` | `UsageRecord` | `org_id`, `metric`, `quantity`, `timestamp` | |
| `webhook_events` | `WebhookEvent` | `provider` enum, `provider_event_id`, `event_type`, `payload` JSONB, `processed`, `error_message`, `received_at` | Unique constraint `uq_webhook_event_provider_event_id` on `(provider, provider_event_id)` — the idempotency backbone |

## Status enums

- `PaymentStatus` (`models/billing.py:29-39`): `CREATED, PENDING, PROCESSING, SUCCEEDED, FAILED, CANCELLED, REFUNDED, PARTIALLY_REFUNDED, DISPUTED`. These match the PayPal Checkout states well (no enum change needed).
- `SubscriptionStatus`: `ACTIVE, PAST_DUE, CANCELED, UNPAID, INCOMPLETE, TRIALING`.
- `InvoiceStatus`: `DRAFT, OPEN, PAID, VOID, UNCOLLECTIBLE`.
- `BillingCycle`: `ONE_TIME, MONTHLY, YEARLY`.
- `PaymentProvider`: `STRIPE, RAZORPAY, MANUAL` — **must add `PAYPAL`**.

## Migration mechanism

- Alembic in `packages/database/alembic/`; baseline + one RLS migration. `env.py` autogenerate-ready against `atlas_db.models`.
- **Enum policy** (`docs/database/ENUM_POLICY.md`): native Postgres ENUMs must be evolved with a **custom migration** using `op.get_context().autocommit_block()` + `ALTER TYPE payment_provider ADD VALUE 'paypal'`. Enum additions are treated as **irreversible**. This is the only required schema change for PayPal; adding the enum value in the model is not enough for Postgres.

## Ownership

- `Organization` / `User` / `OrganizationMember` in `packages/database/atlas_db/models/core.py`. `User.org_id` is a nullable FK; memberships carry role+status. `Payment.org_id` FK → `organizations.id`. JWT claims carry `sub`, `membership_id`, `organization_id` (`apps/backend/schemas/auth.py`).

---

# 4. Existing API architecture

- Routers under `apps/backend/routers/`, mounted in `apps/backend/main.py` under `/api/v1`.
- Auth dependencies in `apps/backend/dependencies.py`: `require_authenticated`, `get_current_user`, `get_current_member`, `require_org_member`; DB session via `get_db_session`. `TokenClaims` carries `organization_id`.
- **Billing routes** (`apps/backend/routers/billing.py`, mounted at `/api/v1/billing`):
  - `GET /plans` → `list[ProductResponse]`
  - `POST /checkout` → `CheckoutRequest(plan_id, provider, success_url, cancel_url, idempotency_key)` → `CheckoutResponse(session_id, url)`
  - `POST /webhooks/stripe` (reads `stripe-signature` header)
  - `POST /webhooks/razorpay` (reads `X-Razorpay-Signature` header)
  - `GET /subscriptions`, `GET /invoices`, `GET /payments`
- **Critical gaps in the billing API:**
  - **No authentication wired on billing routes.** Every org-scoped call mocks `org_id = uuid.uuid4()` (`# Mock org id` at lines 20-21, 59, 124, 131, 138). The rest of Atlas has real auth; billing must be brought in line (`get_current_user`/`TokenClaims.organization_id`).
  - No capture endpoint (Razorpay capture is assumed client-side; Stripe is webhook-driven). PayPal Checkout requires a **server-side capture step**.
  - No payment reconciliation endpoint.
  - No amount/currency client-trust guard: the checkout flow derives amount from the DB `Price` (good), but there is no server-side revalidation path post-approval.
- Error handling: centralized `custom_http_exception_handler`, `validation_exception_handler`, `domain_exception_handler`, `global_exception_handler` (`apps/backend/exceptions.py`); `DomainException` from `packages.execution_engine.domain.exceptions`.
- Background ops: AGENTS.md mandates routing through the Celery `EventBus`. Billing webhooks currently run synchronously; PayPal webhook handling can follow the same synchronous pattern for consistency (capture is user-requested and must be synchronous anyway).

---

# 5. Existing frontend architecture

Audited via `apps/landing` (the live frontend).

**There is no pricing/billing/checkout UI anywhere.** All checkout surface must be built new, matching existing conventions.

- Framework: Vite 8 + React 19 + TypeScript, Tailwind v4 (CSS-first `@theme` tokens), shadcn-style components (cva + Radix `Slot` + `cn()`). Routes in `apps/landing/src/App.tsx` (React Router 7). Nav/sidebar: `src/layouts/WorkspaceLayout.tsx` (`dockItems`) and `src/layouts/PublicLayout.tsx` (Navbar).
- API client: `src/core/api/client.ts` — `apiClient.{get,post,...}` wrapper; base URL from `VITE_API_BASE_URL` (default `http://localhost:8000`); auto-injects `Authorization: Bearer <atlas_token>` from `localStorage`; unwraps `{success, data, message}` envelope; 401 single-flight re-auth (dev only).

**The frontend does not currently send an org id** — org resolution must come from the backend JWT (`TokenClaims.organization_id`).

- Auth: `src/features/auth/services/authService.ts` + `ProtectedRoute.tsx`. localStorage keys `atlas_token`, `atlas_logged_in`, `atlas_current_user`.
- UI patterns to mirror: `src/components/ui/button.tsx` (cva Button), Drawer panels (e.g., `src/features/benchmarks/components/Drawer/index.tsx`, `src/features/models/components/ModelDrawer.tsx`), `Login.tsx` form/loading/error conventions, `MultiStepLoader` + skeletons, framer-motion.
- Env: only `VITE_API_BASE_URL` used. No `NEXT_PUBLIC_*`. `apps/landing/vercel.json` SPA rewrite means PayPal return URLs like `/dashboard/billing?status=...` are reachable with route addition in `App.tsx`.
- **No frontend test framework** (no vitest/jest/testing-library). Convention is ad-hoc Node/Playwright scripts + a route-regex audit (`npm run test:routes`). A checkout component will need vitest added or script-audit conventions followed.

---

# 6. Existing configuration / secrets system

- Backend settings: `apps/backend/config.py` (`Settings`, pydantic-settings, `.env` file). Existing billing keys: `stripe_api_key`, `stripe_webhook_secret`, `razorpay_key_id`, `razorpay_key_secret`, `razorpay_webhook_secret`, with `stripe_enabled`/`razorpay_enabled` properties.
- `.env.example` (repo root, 23 lines) contains only core infra vars (**no billing keys at all**). `.env` is gitignored.
- Vercel: root `vercel.json` (Python function `api/index.py`); `apps/landing/vercel.json` (SPA rewrite). Production deployments push env vars at the Vercel/Render project level, not in-repo.
- Docker: `docker-compose.yml` / `docker-compose.prod.yml` define db/redis/api/worker; env passed via `env_file: .env` (dev) / project secrets (prod). Backend `Dockerfile` builds via `uv sync`.
- **Required new PayPal config (names):**
  - `PAYPAL_ENVIRONMENT=sandbox|live`
  - `PAYPAL_CLIENT_ID=...`
  - `PAYPAL_CLIENT_SECRET=...` (server-side only)
  - `PAYPAL_WEBHOOK_ID=...` (used for webhook signature verification; the verification API needs the webhook id + transmission headers)
  - Frontend will additionally need a client-side `VITE_PAYPAL_CLIENT_ID` (public, safe) for the JS SDK buttons.
- **Security finding:** `razorpay_test_api_keys_1785679957258.csv` is **committed to git** (`git ls-files` confirms) and contains a live Razorpay test key/secret pair. Outside the strict PayPal scope, but it should be purged from history + rotated. No PayPal credentials exist to leak.

---

# 7. Existing test architecture

- pytest via `uv`, config in `pyproject.toml` (`testpaths` = `tests/backend`, `tests/benchmark`, `packages/database/tests`, `services/dataset/tests`, `services/report/tests`; `addopts=-ra -q --cov=packages --cov=services`). `tests/execution` must run separately (`uv run pytest tests/execution -q`) due to a mapper-registry collision — documented in pyproject and docs.
- DB fixtures: SQLite in-memory pattern in `packages/database/tests/conftest.py` (session-scoped `engine`/`init_db`, function-scoped `session`) with SQLite compiler shims for JSONB→JSON and ENUM→VARCHAR. Other test suites (agent, report) define their own local `db_session` fixture with `create_engine("sqlite:///:memory:")` + `Base.metadata.create_all`. Optional real-Postgres pattern exists (`test_d2_postgres_integration.py`, skips if unreachable).
- Mocking conventions: `unittest.mock`/`patch`, `monkeypatch.setenv`, hand-rolled `FakeClient` classes, FastAPI `app.dependency_overrides`, `TestClient`.
- **No httpx MockTransport / VCR / respx anywhere** (a `httpx.MockTransport` is the natural fit for a PayPal REST client and fits repo conventions).
- **No billing/payment tests exist.** `test_billing_integration.py` at repo root is a stale ad-hoc script that imports `services.billing.checkout` — **that module does not exist**; the script is broken and would fail to import.
- CI: `.github/workflows/test.yml` runs ruff, mypy, schema init against a Postgres service container, then `pytest` (so new tests must live in `testpaths` dirs or be added to `testpaths`). `services/billing/tests` does not exist today; it must be created and added to `testpaths`.

---

# 8. Conflicts / risks

1. **Enum migration risk:** Adding `PAYPAL` to `PaymentProvider` requires a custom `ALTER TYPE ... ADD VALUE` migration (ENUM_POLICY.md). Must use `autocommit_block()`; irreversible. If the SQLite dev path (`create_all`) is used, the model change alone suffices for local dev, but Postgres (CI/prod) needs the migration. Migration policy forbids editing the baseline — new migration only.
2. **Billing API is unauthorized/mocked:** Reusing `/api/v1/billing/*` as-is would leak cross-org checkout (payment rows keyed to random UUIDs). The PayPal work must wire real `get_current_user`/`TokenClaims.organization_id` and ownership checks, or it will ship an auth hole. This touches existing stripe/razorpay routes too (shared router) — risk of scope creep; must be done carefully and minimally.
3. **Gateway ABC mismatch for PayPal Checkout:** The existing ABC has `create_checkout_session`, webhook verification, subscription cancel, refund. PayPal Checkout (Orders v2) needs **server-side order create → approval → capture**, and webhook verification differs (transmission-id/transmission-time/transmission-signature/cert-url + webhook id verification API, not HMAC). Plan: keep the ABC's existing four methods, and **add a capture/reconcile capability** (e.g., `capture_payment(...)` and/or `get_order(...)`) that PayPal implements and Stripe/Razorpay can implement as no-ops or best-effort. Must not break existing gateways.
4. **No dependency on a PayPal SDK exists.** `paypalrestsdk` is deprecated; `paypal-checkout-sdk` is heavy and drags `paypalhttp`.

**Recommendation: call the PayPal REST API directly with `httpx` (already a declared dependency), implementing the OAuth token + Orders v2 endpoints.** Fits "no unnecessary dependencies" and "domain layer must not depend on provider SDK" rules.

5. **Webhook trust model:** PayPal webhooks verify via `POST /v1/notifications/verify-webhook-signature` using `PAYPAL_WEBHOOK_ID` + transmission headers. Local dev needs a tunnel (e.g., ngrok) for PayPal to reach the local webhook. Sandbox webhooks must be configured in the PayPal developer dashboard. Also PayPal webhook headers differ from Stripe/Razorpay — the router/`verify_webhook_signature` abstraction must pass them through.
6. **Credit/entitlement activation is entirely unimplemented.** `CreditAccount`/`CreditTransaction` are dormant. Activation must: find/create the org's credit account, credit the `Price`'s implied value, insert a `CreditTransaction` (reference the `Payment.id`), and be idempotent (guard on `Payment.status` transition CREATED→SUCCEEDED and on transaction reference uniqueness). Risk: double-grant if both webhook and capture-complete path run; the existing `WebhookEvent` uniqueness + payment status guard is the right mechanism.
7. **Idempotency stub in create_checkout_session:** the idempotency_key check is a no-op (`pass`). For PayPal, reuse of `Payment.idempotency_key` should return the existing order instead of creating a second PayPal order. Needs a small service change.
8. **Amount/currency trust:** The server derives amount/currency from the DB `Price` at order creation (good). Capture/reconcile must re-verify the captured PayPal amount against the stored `Payment` amount to detect tampering, and store PayPal's `purchase_units[].payments.captures[].amount`.
9. **RLS:** `81db55ad9a77` enabled default-deny RLS on backend-only tables. Any new tables (none currently required) or new DB access must respect RLS; the existing billing tables already carry the RLS wiring — verify the new enum migration does not trip RLS.
10. **Frontend has no org/billing surface and no test framework.** Building a billing page means new routes, nav entries, an env var, and either vitest (new devDependency) or script-audit conventions.
11. **Stale/broken artifacts:** root `test_billing_integration.py` (imports missing `services.billing.checkout`), `apps/web` dead stub, empty `apps/admin`, committed Razorpay test keys CSV, `docs/AGENT_HANDOFF.md` partially stale re frontend. These are out of PayPal scope but worth flagging.
12. **git/PR hygiene:** branch must stay isolated; no commits from other feature branches. Worktree at `D:\atlas-paypal` keeps the dirty `D:\atlas` (pr35 recovery) untouched.

---

# 9. Proposed architecture

The PayPal integration is designed **around the existing Atlas billing subsystem** — the smallest coherent change that fits conventions. It does NOT introduce a parallel billing layer.

## Conceptual layers (matches the existing structure)

```
Atlas API (apps/backend/routers/billing.py)        <- real auth, org from JWT
        |
BillingService (services/billing/service.py)      <- order create, capture, reconcile, activate credits
        |
PaymentGateway ABC (services/billing/gateways/base.py)
        |
PayPalGateway (services/billing/gateways/paypal_provider.py)   <- new
        |
PayPal REST API (OAuth2 token, Orders v2, capture, webhook verification) via httpx
```

## Modules/files to add

| Path | Purpose |
|---|---|
| `services/billing/gateways/paypal_provider.py` | `PayPalGateway(PaymentGateway)`: OAuth token (cached), create order (with approve URL), capture order, get order, verify webhook signature (verification API), refund (best-effort). Uses `httpx` directly. |
| `packages/database/alembic/versions/<rev>_add_paypal_to_payment_provider.py` | Custom migration: `ALTER TYPE payment_provider ADD VALUE 'paypal'` (irreversible, per ENUM_POLICY.md). |
| `services/billing/tests/` (new) | `test_paypal_gateway.py`, `test_billing_service_paypal.py`, `test_paypal_webhooks.py`, `conftest.py` (SQLite in-memory + httpx MockTransport). Must be added to `testpaths` in `pyproject.toml`. |
| `docs/paypal_integration.md` | Sandbox/live setup, webhook setup, security, deployment, limitations. |

## Modules/files to modify

| Path | Change |
|---|---|
| `packages/database/atlas_db/models/billing.py` | Add `PAYPAL = "paypal"` to `PaymentProvider` enum. |
| `services/billing/gateways/base.py` | Add provider-agnostic capture/reconcile capability to the ABC (e.g., `capture_payment(provider_order_id, amount, currency)`) with safe defaults so Stripe/Razorpay keep compiling. |
| `services/billing/registry.py` | Add `PAYPAL` branch + `settings.paypal_enabled` guard. |
| `apps/backend/config.py` | Add `paypal_environment`, `paypal_client_id`, `paypal_client_secret`, `paypal_webhook_id` + `paypal_enabled` property. |
| `services/billing/service.py` | Implement idempotent order creation (reuse existing `Payment.idempotency_key`), `capture_payment`, payment reconciliation, and **credit/entitlement activation** (idempotent, guarded on status transition + `CreditTransaction.reference_id`). |
| `apps/backend/routers/billing.py` | Wire real auth/org resolution on all org-scoped routes (fix the mock `org_id` hole), add `POST /capture/{payment_id}`, `POST /webhooks/paypal`. |
| `apps/backend/schemas/billing.py` | `CaptureRequest/CaptureResponse`; ensure `CheckoutResponse` carries PayPal order id + approve URL (existing shape already fits). |
| `.env.example` | Add placeholder `PAYPAL_ENVIRONMENT`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID` (placeholders only). |
| `pyproject.toml` | Add `services/billing/tests` to `testpaths`. |
| `apps/landing` | New billing/checkout surface: `src/features/billing/` (service + PayPal buttons component + success/cancel/failure states), route in `App.tsx`, nav entry in `WorkspaceLayout.tsx`, `VITE_PAYPAL_CLIENT_ID` support. |

## Database changes

- Only: add `PAYPAL` to `payment_provider` ENUM via new migration. No new tables/columns — `Payment.provider_order_id` (PayPal order id), `provider_payment_id` (capture id), `metadata_json`, `idempotency_key` already cover the PayPal Checkout model. Credit activation uses existing `credit_accounts`/`credit_transactions`.

## API endpoints (proposed)

- `POST /api/v1/billing/checkout` — extend existing; accepts `provider=paypal`; returns PayPal order id + approval URL (reuse `CheckoutResponse`).
- `POST /api/v1/billing/capture/{payment_id}` — authenticated; server-side capture of an approved PayPal order; returns capture status + payment record.
- `GET /api/v1/billing/payments/{payment_id}` — authenticated; reconciliation/status lookup.
- `POST /api/v1/billing/webhooks/paypal` — PayPal webhook verification + idempotent processing via existing `BillingService.process_webhook` path.

## Provider abstraction design

- Keep `PaymentGateway` as the seam. PayPal implements the four existing methods + a capture/reconcile method. The `BillingService` (domain/application layer) never imports `httpx` or PayPal types; only `PaymentProvider`/gateway interfaces cross the boundary. `CheckoutSessionResult(session_id, url)` maps naturally to PayPal (`id` + `links[rel=approve].href`).

## Frontend flow

- New `Pricing`/`Billing` page (marketing route or `/dashboard/billing`) lists `GET /billing/plans`; `PayPalButtons` component loads PayPal JS SDK (`https://www.paypal.com/sdk/js?client-id=...&intent=capture`), `onCreateOrder` calls backend `POST /billing/checkout` (returns PayPal order id), `onApprove` calls backend `POST /billing/capture/{payment_id}`; success/cancel/failure states rendered per existing UI conventions.

**Frontend never touches the client secret and never calls PayPal privileged APIs.**

## Webhook design

- `POST /api/v1/billing/webhooks/paypal`: pass PayPal transmission headers (`paypal-transmission-id`, `paypal-transmission-time`, `paypal-transmission-sig`, `paypal-cert-url`, `paypal-auth-algo`) into `PayPalGateway.verify_webhook_signature` which calls the PayPal verify API using `PAYPAL_WEBHOOK_ID`. Process `CHECKOUT.ORDER.APPROVED` / `PAYMENT.CAPTURE.COMPLETED` (and `PAYMENT.CAPTURE.DENIED`/`REFUNDED`) through the existing idempotent `WebhookEvent` machinery. Entitlement activation happens only on verified capture completion, never on a frontend callback alone.

## Environment variables (names only, no values)

```
PAYPAL_ENVIRONMENT=sandbox
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
PAYPAL_WEBHOOK_ID=
VITE_PAYPAL_CLIENT_ID=        # frontend (public, mirrors PAYPAL_CLIENT_ID in dev)
```

## Testing strategy

- Gateway unit tests with `httpx.MockTransport` (OAuth token ok/fail, create order ok/fail, capture ok/fail, network timeout) — no live PayPal calls.
- Domain/service tests on SQLite in-memory (idempotency, status transitions, duplicate webhook, unknown payment, credit activation once, invalid transition).
- API tests with `app.dependency_overrides` (unauthorized, wrong org, invalid plan, manipulated amount, full happy-path flow).
- Frontend: follow existing conventions (route audit script; optional vitest addition for the checkout component).
- CI: new tests run via default `pytest` once `services/billing/tests` is in `testpaths`.

## Implementation phases (dependency-ordered)

- **Phase A — Database/domain:** enum model + `PAYPAL` value + migration.
- **Phase B — Config:** PayPal settings + `.env.example` placeholders.
- **Phase C — Provider/client:** `PayPalGateway` (OAuth, orders, capture, webhook verify) with httpx; extend ABC with capture; register in `GatewayRegistry`.
- **Phase D — Service layer:** idempotent checkout, capture, reconciliation, credit/entitlement activation.
- **Phase E — API:** auth wiring on billing router, capture + webhook endpoints, schemas.
- **Phase F — Frontend:** billing service, PayPal buttons component, page, routes, nav, env var.
- **Phase G — Tests:** gateway/service/webhook/API tests.
- **Phase H — Documentation:** `docs/paypal_integration.md`, update this audit report, `.env.example`.

---

# 10. Implementation phases

Covered in section 9 ("Implementation phases") above: **A → H** with explicit dependencies.

---

# 11. Explicit non-goals

This implementation will NOT attempt:

- Marketplace creator payouts / multi-party PayPal marketplace settlement.
- Domestic Indian PayPal payment support (PayPal India restrictions are out of scope; Razorpay remains the INR path).
- Tax/legal automation (invoice tax fields already exist but are not computed).
- Refund automation beyond what the existing `Refund` model/ABC `refund_payment` already provide (no new refund UI/flow).
- Recurring subscription billing automation via PayPal (no Billing Agreements/Plans). PayPal here is one-time Checkout; subscription support stays Stripe/Razorpay-shaped and is not expanded.
- Redesign of the database or execution-service architecture.
- Replacing the existing Stripe/Razorpay gateways or their behavior.
- Adding a generic multi-tenant "payment gateway" framework beyond the existing `PaymentGateway` ABC.
- Purge/rotation of the committed Razorpay test keys (flagged, but outside PayPal scope).
- Any change to the `apps/web` stub, `apps/admin`, or unrelated CI/config.

---

*Report end. Implementation has not begun; per the task, the next step is the Phase 3 implementation-readiness report.*

---