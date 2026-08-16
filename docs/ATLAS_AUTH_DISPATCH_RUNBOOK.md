# Atlas Auth & Dispatch Runbook

> **Self-contained for any agent or developer with zero prior context.**
> Last updated: 2026-08-16 | Branch: `wire_real_llm_adapter`

---

## 1. Atlas Architecture (Authentication Relevant)

```
Browser
  │
  ├─ http://localhost:5173   ← Vite frontend (React + TypeScript)
  │     │
  │     ├─ authService.ts   ← SOLE auth authority — only real JWTs
  │     └─ client.ts        ← API transport with single-flight 401 recovery
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
| **Canonical branch** | `wire_real_llm_adapter` |
| **Canonical worktree** | `C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\wire_real_llm_adapter` |
| **Canonical database** | `<worktree>\atlas_dev.db` |
| **Frontend URL** | `http://localhost:5173` |
| **Backend URL** | `http://localhost:8000` |
| **Evaluation page** | `http://localhost:5173/dashboard/evaluations/new` |
| **Frontend port** | `5173` (bound `0.0.0.0:5173` — both IPv4 and IPv6) |
| **Backend port** | `8000` (bound `0.0.0.0:8000` — both IPv4 and IPv6) |
| **Database config** | `.env`: `DATABASE_URL=sqlite:///./atlas_dev.db` |
| **Demo credentials** | `demo@atlas.val` / `password123` |

---

## 3. Startup Procedure

### Canonical startup (recommended):
```bat
cd C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\wire_real_llm_adapter
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
cd C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\wire_real_llm_adapter

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
authService.loginUser()
  → POST /api/v1/auth/login (NO Authorization header)
  → Backend issues JWT (HS256, exp = now + 60 min)
  → setValidatedAuthToken(token)   ← rejects non-JWT strings
  → localStorage.setItem('atlas_token', token)

Protected request:
  → client.ts reads localStorage.getItem('atlas_token')
  → Adds Authorization: Bearer <token>
  → Backend validates via jwt.decode(token, settings.jwt_secret)

On 401 (expired/invalid token):
  → client.ts performReAuth() — raw fetch /auth/login — NO Auth header
  → Single-flight: concurrent 401s share ONE login attempt
  → New token stored via setAuthToken()
  → Original request retried ONCE
  → If retry also 401: token cleared, real error thrown — NO infinite loop

On logout:
  → localStorage.removeItem('atlas_token')
  → Legacy keys also cleared: atlas_registered_users, atlas_current_user
```

---

## 6. Token Storage Invariants

```
localStorage.atlas_token must ALWAYS be:
  ✅ A real backend-issued JWT (3 dot-separated base64 segments)
  ✅ Signed with settings.jwt_secret ("dev-secret-key-do-not-use-in-production")

localStorage.atlas_token must NEVER be:
  ❌ local_token_*   (fake token from old local auth fallback — now removed)
  ❌ undefined
  ❌ null (if user is supposed to be authenticated)
  ❌ A 2-segment or 1-segment string
```

`setValidatedAuthToken()` in `authService.ts` **throws** if a non-JWT is passed — this is the enforcement point.

---

## 7. Authentication Implementation

### Backend (`apps/backend/services/auth.py`)
- `authenticate_user()`: looks up user by email, verifies Argon2 password hash, issues JWT via `create_access_token()`
- JWT payload: `{ sub: user_id, exp: now+60min, iat: now, jti: uuid4() }`
- JWT secret: `settings.jwt_secret` (from `.env` or default `"dev-secret-key-do-not-use-in-production"`)

### Frontend Auth Authority (`apps/landing/src/features/auth/services/authService.ts`)
- `loginUser()`: backend-only, real error on failure — NO fake token fallback
- `setValidatedAuthToken()`: runtime invariant enforcement — throws on non-JWT
- `ensureAuthenticatedSession()`: used by auth context on load, attempts one login if token missing/expired

### Frontend Transport (`apps/landing/src/core/api/client.ts`)
- `performReAuth()`: single-flight re-auth using raw fetch (not apiClient — avoids circular dependency)
- All 401s on protected endpoints trigger at most ONE re-auth attempt, then ONE retry
- `isStructurallyValidJwt()`: validates tokens before storing

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
# Login and get JWT
$r = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method POST `
  -ContentType "application/json" `
  -Body '{"username":"demo@atlas.val","email":"demo@atlas.val","password":"password123"}'
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
cd C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\wire_real_llm_adapter
node apps/landing/scripts/auth-e2e-dispatch.js
```

### Expected successful output:
```
✅ Backend healthy.
BEFORE FIX: local_token_* → GET /api/v1/executions → HTTP 401
✅ Confirmed: local_token_* is REJECTED by backend with 401

Scenario 1 (Clean Browser):           ✅ PASSED — JWT valid, 201, COMPLETED, 0 unexpected 401s
Scenario 2 (Returning Valid Session):  ✅ PASSED — JWT valid, 201, COMPLETED, 0 login calls
Scenario 3 (Invalid JWT Recovery):     ✅ PASSED — invalid JWT → 1 login call → 201 → COMPLETED
Scenario 4 (Sequential Dispatches):    ✅ PASSED — 3× 201, 0 unexpected 401s

✨ ALL HARDENED AUTHENTICATION & DISPATCH SCENARIOS PASSED!
```

---

## 11. Known Historical Failures & Root Causes

| # | Failure | Root cause proven | Fix applied |
|---|---|---|---|
| 1 | `localhost` → wrong Vite server | `D:\atlas\start_frontend.cmd` serving stale server on IPv6 `[::1]` | Vite bound to `0.0.0.0`; old launcher neutralized |
| 2 | GET /benchmarks, GET /executions → 401 | Stale backend from `implement_atlas_agent_loop` worktree occupying port 8000 with different auth DB | Backend port guard added; Uvicorn bound to `0.0.0.0` |
| 3 | POST /auth/login → 401 | `client.ts` was sending `Authorization: Bearer <stale_token>` header on the login request itself | Removed: `/auth/login` endpoint never receives `Authorization` header |
| 4 | **Recurring 401 after successful login** | `authService.ts` had a 4-step local fallback chain that issued fake `local_token_*` strings when backend login threw any error. These `local_token_*` strings always fail `jwt.decode()` in the backend | **Removed entire local fallback chain.** `loginUser()` returns real JWT or real error. `setValidatedAuthToken()` throws on non-JWT |
| 5 | Dual auto-login pathways | `client.ts` had its own independent `/auth/login` call in `getOrFetchToken()`, creating race conditions with `authService.ts` that could overwrite good tokens | Removed `getOrFetchToken()` auto-login; `client.ts` uses single-flight `performReAuth()` via raw fetch |

---

## 12. Troubleshooting

### Symptom: HTTP 401 on GET /executions or GET /benchmarks after login

1. Check `localStorage.atlas_token` in browser DevTools:
   - If it starts with `local_token_` → **old code bug, should be fixed**. Clear localStorage and re-login.
   - If it looks like a JWT → proceed to step 2.
2. Verify backend process: `Get-NetTCPConnection -LocalPort 8000 -State Listen` → confirm PID is from `wire_real_llm_adapter` worktree.
3. Verify backend DB: `settings.database_url` must point to canonical `atlas_dev.db`.
4. Re-run regression test: `node apps/landing/scripts/auth-e2e-dispatch.js`.

### Symptom: Black screen / no routes at `/dashboard/evaluations/new`

1. Check browser URL — must be `http://localhost:5173` not `http://localhost:3000`.
2. Check which Vite server is running: `Get-NetTCPConnection -LocalPort 5173 -State Listen`.
3. Confirm PID CommandLine contains `wire_real_llm_adapter`.
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
