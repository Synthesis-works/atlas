# Atlas Development Environment Invariants

This document defines the canonical environment setup, port configuration, security guards, and regression testing procedures for Project Atlas.

---

## 1. Canonical Worktree & Database Specifications

| Component | Canonical Location / Setting |
|---|---|
| **Git Repository** | `Synthesis-works/atlas` |
| **Canonical Worktree** | `C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\wire_real_llm_adapter` |
| **Canonical Database** | `C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\wire_real_llm_adapter\atlas_dev.db` |
| **Frontend App** | `apps/landing` (`http://localhost:5173` & `http://127.0.0.1:5173`) |
| **Backend API** | `apps.backend.main:app` (`http://127.0.0.1:8000`) |

---

## 2. Port & Dual-Stack Network Invariants

- **Frontend Port `5173`**: Bound to `0.0.0.0:5173` (dual-stack IPv4 `127.0.0.1` and IPv6 `[::1]`). Both `localhost` and `127.0.0.1` reach the canonical Vite instance.
- **Backend Port `8000`**: Bound to `127.0.0.1:8000`.

---

## 3. Required Startup Security Guards

1. **Frontend Port Guard** (`apps/landing/scripts/check-port.js`):
   - Audits all listeners on port 5173 across IPv4 and IPv6.
   - Auto-terminates foreign processes (e.g. from `D:\atlas` or other worktrees) before Vite boots.

2. **Backend Port Guard** (`scripts/check-backend-port.js`):
   - Audits all listeners on port 8000 across IPv4 and IPv6.
   - Auto-terminates foreign backend processes (e.g. from `implement_atlas_agent_loop` or other worktrees) before Uvicorn boots.

3. **Obsolete Launcher Neutralization**:
   - `D:\atlas\start_frontend.cmd` is explicitly disabled to prevent launching stale Vite instances.

---

## 4. Authentication Invariants

- **`POST /api/v1/auth/login`**: MUST NEVER receive an `Authorization: Bearer ...` header. Injected headers cause FastAPI authentication middleware to reject login requests with `401 Unauthorized`.
- **JWT Storage Key**: `atlas_token` in `localStorage`.
- **Single Redirection Source**: `ProtectedRoute.tsx` is the sole authorization guard for dashboard routes.

---

## 5. E2E Regression Testing Commands

To verify environment stability and run full real-browser E2E authentication & execution dispatch tests:

```powershell
# 1. Run all frontend & backend startup guards + launch servers
.\start_atlas_dev.bat

# 2. Run dual-origin route & DOM verification test
node apps/landing/scripts/browser-forensic-test.js

# 3. Run complete auth & execution dispatch E2E suite (Clean scratch, Returning, Expired recovery)
node apps/landing/scripts/auth-e2e-dispatch.js
```
