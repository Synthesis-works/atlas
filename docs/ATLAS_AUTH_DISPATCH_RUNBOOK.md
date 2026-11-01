# Atlas Auth & Dispatch Runbook

> **Self-contained for any agent or developer with zero prior context.**
> Last updated: 2026-10-31 | Branch: `feature/auth-hardening`

---

## 1. Atlas Architecture (Authentication Relevant)

```
Browser
  │
  ├─ http://localhost:5173   ← Vite frontend (React + TypeScript)
  │     │
  │     ├─ AuthProvider.tsx  ← SOLE client auth authority (via /auth/me)
  │     └─ client.ts         ← API transport; clears session on 401
  │
  └─ http://localhost:8000   ← FastAPI backend (Python / SQLAlchemy)
        │
        ├─ /api/v1/auth/login      ← issues JWTs
        ├─ /api/v1/benchmarks/...  ← protected (requires Bearer JWT)
        ├─ /api/v1/executions/...  ← protected (requires Bearer JWT)
        └─ atlas_dev.db            ← canonical SQLite database
              │
              └─ execution_runner.py  ← background worker (Groq/LLM)
```

---

## 2. Canonical Environment

| Component | Value |
|---|---|
| **Git repository** | `Synthesis-works/atlas` |
| **Canonical branch** | `main` (work on a feature branch; never commit auth changes directly to `main`) |
| **Canonical worktree** | `D:\atlas` |
| **Canonical database** | `<worktree>\atlas_dev.db` |
| **Frontend URL** | `http://localhost:5173` |
| **Backend URL** | `http://localhost:8000` |
| **Evaluation page** | `http://localhost:5173/dashboard/evaluations/new` |
| **Frontend port** | `5173` (bound `0.0.0.0:5173` — both IPv4 and IPv6) |
| **Backend port** | `8000` (bound `0.0.0.0:8000` — both IPv4 and IPv6) |
| **Database config** | `.env`: `DATABASE_URL=sqlite:///./atlas_dev.db` |
| **Development account** | Optional seed: `demo@atlas.val` / `password123` (local dev/CLI/E2E only — the web app never logs in automatically) |

---

## 3. Startup Procedure

### Canonical startup (recommended):
```bat
cd D:\atlas
.\start_atlas_dev.bat
```

`start_atlas_dev.bat` will:
1. Verify it is running from the canonical worktree
2. Run backend port 8000 security guard (kills foreign processes)
3. Run frontend port 5173 security guard (kills foreign processes)
4. Set `DATABASE_URL` to the absolute canonical path
5. Set `PYTHONPATH` for all local packages
6. Start Uvicorn backend (`0.0.0.0:8000`)
7. Start Vite frontend (`0.0.0.0:5173`)
8. Start execution worker
9. Poll backend `/health` endpoint until ready

### Manual startup (if bat file fails):
```powershell
cd D:\atlas

# Backend
$env:PYTHONPATH="packages/database;packages;services;."
$env:DATABASE_URL="sqlite:///./atlas_dev.db"
$env:CELERY_TASK_ALWAYS_EAGER="true"
uv run python -m uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
npm --prefix apps/landing run dev

# Execution worker (separate terminal)
$env:PYTHONPATH="packages/database;packages;services;."
$env:DATABASE_URL="sqlite:///./atlas_dev.db"
$env:CELERY_TASK_ALWAYS_EAGER="true"
uv run python -m apps.backend.worker.execution_runner
```

---

## 4. Authentication Endpoints

| Endpoint | Method | Auth required | Purpose |
|---|---|---|---|
| `/api/v1/auth/login` | POST | ❌ NEVER | Issue JWT |
| `/api/v1/auth/register` | POST | ❌ | Create user |
| `/api/v1/auth/me` | GET | ✅ Bearer JWT | Get current user |
| `/api/v1/executions` | GET | ✅ Bearer JWT | List executions |
| `/api/v1/benchmarks` | GET | ✅ Bearer JWT | List benchmarks |
| `/api/v1/benchmarks/{id}/executions` | POST | ✅ Bearer JWT | Dispatch evaluation |

---

## 5. JWT Lifecycle

```
AuthProvider.signIn(email, password)
  → authService.signIn()
  → POST /api/v1/auth/login { email, password } (NO Authorization header)
  → Backend issues JWT (HS256, exp = now + settings.jwt_access_expire_minutes)
  → token stored in localStorage['atlas_token']
  → GET /api/v1/auth/me confirms the token belongs to a usable account
  → AuthProvider state = 'authenticated'

Protected request:
  → client.ts reads localStorage.getItem('atlas_token')
  → Adds Authorization: Bearer <token>
  → Backend validates via jwt.decode(token, settings.jwt_secret)

On 401 (expired/invalid token):
  → client.ts clears atlas_token and legacy keys
  → Emits `atlas:auth-session-cleared`
  → AuthProvider state = 'unauthenticated'; ProtectedRoute redirects to /login
  → NO automatic re-auth, NO retry, NO fake session

On logout:
  → clearAuthSession() removes atlas_token and legacy keys
  → Emits `atlas:auth-session-cleared`
```

---

## 6. Token Storage Invariants

```
localStorage.atlas_token must ALWAYS be:
  ✅ A real backend-issued JWT (3 dot-separated base64 segments)

localStorage.atlas_token must NEVER be:
  ❌ local_token_*   (fake token from the retired local fallback)
  ❌ undefined
  ❌ null (if user is supposed to be authenticated)
  ❌ A 2-segment or 1-segment string

Retired keys (must be absent; they are purged on load):
  ❌ atlas_logged_in
  ❌ atlas_current_user
  ❌ atlas_registered_users
```

`setValidatedAuthToken()` in `authService.ts` **throws** if a non-JWT is passed — this is the enforcement point.

---

## 7. Authentication Implementation

### Backend (`apps/backend/services/auth.py`)
- `authenticate_user()`: looks up the user by lowercase, trimmed email, verifies the Argon2 hash, then issues a JWT via `create_access_token()`.
- Unknown emails still run a dummy Argon2 verification so failed logins take comparable time.
- Every credential failure returns the same `401` with `Invalid email or password`; disabled accounts only return `403` after the password is proven correct.
- Login payload is `{ email, password }` only. `username`/`identifier` fallbacks are rejected by `UserLogin`.
- JWT payload: `{ sub: user_id, exp, iat, jti }` plus optional membership/org claims.
- JWT secret: `settings.jwt_secret` (from `.env` or the development default).

### Frontend Auth Authority (`apps/landing/src/features/auth/`)
- `AuthProvider.tsx`: single source of client auth state (`loading | authenticated | unauthenticated`). Bootstraps with `/auth/me`, reacts to `atlas:auth-session-cleared` and cross-tab storage events.
- `services/authService.ts`: `signIn()` / `signUp()` call the backend and never fake a session. `ensureAuthenticatedSession()` only validates/purges a stored token; it never logs in.
- `Login.tsx`: email + password only, generic error message, no demo/SSO buttons, no Remember Me, no Forgot Password (no reset backend exists yet).

### Frontend Transport (`apps/landing/src/core/api/client.ts`)
- `atlas_token` is the only credential it reads.
- A protected-endpoint `401` clears the session once and emits `atlas:auth-session-cleared`; it never retries or logs in.
- `/auth/login` and `/auth/register` are exempt from the `Authorization` header.

### Current limitations
- **No password reset / email delivery.** The login page intentionally exposes no "Forgot password" flow because the backend has no reset-token or mail capability. This is a documented TODO, not a working feature.
- **No "Remember Me".** Sessions use `localStorage` for the single JWT; there is no second persistence mode.
- **Disabled users keep an existing JWT until it expires.** `require_authenticated` validates token claims only; disabling an account does not revoke already-issued tokens.

---

## 8. Port Security Guards

Both guards auto-terminate foreign processes (from other Atlas worktrees) before launching:

| Guard | File | Port |
|---|---|---|
| Backend | `scripts/check-backend-port.js` | 8000 |
| Frontend | `apps/landing/scripts/check-port.js` | 5173 |

Obsolete `D:\atlas\start_frontend.cmd` launcher has been neutralized.

---

## 9. Manual Verification

### Verify backend authentication:
```powershell
# Login and get JWT (email + password only)
$r = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method POST `
  -ContentType "application/json" `
  -Body '{"email":"demo@atlas.val","password":"password123"}'
$token = $r.data.access_token
Write-Host "Token: $($token.Substring(0,50))..."

# Use JWT on protected endpoint
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/executions" `
  -Headers @{ Authorization = "Bearer $token" }
```

### Manually dispatch an evaluation:
```powershell
$dispatch = Invoke-RestMethod -Uri `
  "http://localhost:8000/api/v1/benchmarks/00000000-0000-0000-0000-000000000005/executions" `
  -Method POST -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer $token" } `
  -Body '{"target_model":"groq/llama-3.1-8b-instant"}'
Write-Host "Execution ID: $($dispatch.data.id)"
```

### Inspect the database:
```powershell
uv run python -c "
import sqlite3; conn = sqlite3.connect('atlas_dev.db')
cur = conn.cursor()
cur.execute('SELECT id,email,is_active FROM users LIMIT 5')
for r in cur.fetchall(): print(r)
"
```

### Detect foreign worktree processes:
```powershell
Get-NetTCPConnection -LocalPort 8000,5173 -State Listen | ForEach-Object {
  $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)"
  [PSCustomObject]@{ Port=$_.LocalPort; PID=$_.OwningProcess; CmdLine=$proc.CommandLine }
}
```

---

## 10. E2E Regression Test

### Run command:
```powershell
$env:ATLAS_E2E_EMAIL="demo@atlas.val"
$env:ATLAS_E2E_PASSWORD="password123"
node apps/landing/scripts/auth-e2e-dispatch.js
```

The suite requires a real seeded account and refuses to run without
`ATLAS_E2E_EMAIL` / `ATLAS_E2E_PASSWORD`.

### Expected successful output:
```
============================================================
🛡️  ATLAS AUTH SESSION REGRESSION SUITE
============================================================

🧪 Scenario 1: clean browser login
  ✅ PASSED — stores a structurally valid JWT
  ✅ PASSED — does not write atlas_logged_in
  ✅ PASSED — calls /auth/login exactly once

🧪 Scenario 2: valid pre-seeded JWT
  ✅ PASSED — valid session reaches workspace

🧪 Scenario 3: invalid JWT is rejected without automatic re-auth
  ✅ PASSED — invalid token redirects to /login
  ✅ PASSED — invalid token is cleared
  ✅ PASSED — no automatic re-auth attempt

🧪 Scenario 4: sign out clears the session
  ✅ PASSED — sign out clears atlas_token
  ✅ PASSED — sign out leaves the workspace
```

---

## 11. Known Historical Failures & Root Causes

| # | Failure | Root cause proven | Fix applied |
|---|---|---|---|
| 1 | `localhost` → wrong Vite server | `D:\atlas\start_frontend.cmd` serving stale server on IPv6 `[::1]` | Vite bound to `0.0.0.0`; old launcher neutralized |
| 2 | GET /benchmarks, GET /executions → 401 | Stale backend from `implement_atlas_agent_loop` worktree occupying port 8000 with different auth DB | Backend port guard added; Uvicorn bound to `0.0.0.0` |
| 3 | POST /auth/login → 401 | `client.ts` was sending `Authorization: Bearer <stale_token>` header on the login request itself | Removed: `/auth/login` endpoint never receives `Authorization` header |
| 4 | **Recurring 401 after successful login** | `authService.ts` had a 4-step local fallback chain that issued fake `local_token_*` strings when backend login threw any error. These `local_token_*` strings always fail `jwt.decode()` in the backend | **Removed entire local fallback chain.** Sign-in returns a real JWT or a real error. `setValidatedAuthToken()` throws on non-JWT |
| 5 | Dual auto-login pathways | `client.ts` had its own independent `/auth/login` call, creating race conditions with `authService.ts` that could overwrite good tokens | Removed every auto-login path; `client.ts` clears the session on 401 and never re-authenticates |
| 6 | **Automatic demo login** | The login page prefilled `demo@atlas.val` and `client.ts` re-authenticated with demo credentials on any 401 | Removed demo defaults, the dev-only 401 re-auth, and `atlas_logged_in` as an auth authority. AuthProvider + `/auth/me` are the only session source |

---

## 12. Troubleshooting

### Symptom: HTTP 401 on GET /executions or GET /benchmarks after login

1. Check `localStorage.atlas_token` in browser DevTools:
   - If it starts with `local_token_` → **retired fake token**. Clear localStorage and sign in again.
   - If it looks like a JWT → proceed to step 2.
2. Verify backend process: `Get-NetTCPConnection -LocalPort 8000 -State Listen` → confirm the PID belongs to this repository.
3. Verify backend DB: `settings.database_url` must point to canonical `atlas_dev.db`.
4. Re-run regression test: `node apps/landing/scripts/auth-e2e-dispatch.js`.

### Symptom: Black screen / no routes at `/dashboard/evaluations/new`

1. Check browser URL — must be `http://localhost:5173` not `http://localhost:3000`.
2. Check which Vite server is running: `Get-NetTCPConnection -LocalPort 5173 -State Listen`.
3. Confirm PID CommandLine contains `D:\atlas`.
4. Kill any foreign Vite process, run `node apps/landing/scripts/check-port.js`, restart Vite.

### Symptom: Execution stays QUEUED forever

The execution worker is not running. Start it:
```powershell
$env:PYTHONPATH="packages/database;packages;services;."
$env:DATABASE_URL="sqlite:///./atlas_dev.db"
$env:CELERY_TASK_ALWAYS_EAGER="true"
uv run python -m apps.backend.worker.execution_runner
```

### Symptom: `ModuleNotFoundError: No module named 'atlas_db'`

`PYTHONPATH` is not set. Run with:
```powershell
$env:PYTHONPATH="packages/database;packages;services;."
uv run python -m uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000
```
