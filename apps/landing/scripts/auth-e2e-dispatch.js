/**
 * Atlas Authentication Session E2E Regression Suite
 *
 * Verifies the single-authority model:
 *   - `atlas_token` is the only credential; `atlas_logged_in` is never written.
 *   - A successful login stores a real backend-issued JWT.
 *   - A valid pre-seeded JWT reaches the workspace.
 *   - An invalid JWT is cleared and redirects to /login with NO automatic re-auth.
 *   - Signing out clears the token and leaves the workspace.
 *
 * Required environment:
 *   ATLAS_E2E_EMAIL      email of a real seeded account
 *   ATLAS_E2E_PASSWORD   its password
 *
 * Optional:
 *   ATLAS_E2E_BASE_URL   frontend origin (default http://localhost:5173)
 *   ATLAS_E2E_BACKEND_URL backend origin (default http://localhost:8000)
 */

import { chromium } from 'playwright';

const BASE_URL = process.env.ATLAS_E2E_BASE_URL || 'http://localhost:5173';
const BACKEND_URL = process.env.ATLAS_E2E_BACKEND_URL || 'http://localhost:8000';
const EMAIL = process.env.ATLAS_E2E_EMAIL;
const PASSWORD = process.env.ATLAS_E2E_PASSWORD;

const results = [];

function record(name, passed, detail = '') {
  results.push({ name, passed, detail });
  console.log(`  ${passed ? '✅ PASSED' : '❌ FAILED'}${detail ? ` — ${detail}` : ''}`);
}

async function waitForBackend(timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${BACKEND_URL}/health`, { signal: AbortSignal.timeout(2000) });
      if (res.ok) return true;
    } catch {
      // keep waiting
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

async function getRealJwt() {
  const res = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  if (!res.ok) throw new Error(`Login failed with HTTP ${res.status}`);
  const data = await res.json();
  const token = data?.data?.access_token || data?.access_token;
  if (!token) throw new Error('Backend did not return an access_token');
  return token;
}

function isStructurallyValidJwt(token) {
  if (!token || token.startsWith('local_token_')) return false;
  const parts = token.split('.');
  if (parts.length !== 3) return false;
  try {
    JSON.parse(Buffer.from(parts[1], 'base64').toString());
    return true;
  } catch {
    return false;
  }
}

function corruptSignature(jwt) {
  const parts = jwt.split('.');
  return `${parts[0]}.${parts[1]}.INVALIDSIGNATUREXXXXXXXXXXXXXXXXXXXXXXXXXXX`;
}

function trackLoginCalls(page) {
  const state = { count: 0 };
  page.on('request', (req) => {
    if (req.url().includes('/api/v1/auth/login') && req.method() === 'POST') state.count++;
  });
  return state;
}

async function newPage(browser) {
  const context = await browser.newContext();
  const page = await context.newPage();
  const loginCalls = trackLoginCalls(page);
  return { context, page, loginCalls };
}

async function scenarioCleanLogin(browser) {
  console.log('\n🧪 Scenario 1: clean browser login');
  const { context, page, loginCalls } = await newPage(browser);
  try {
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await page.locator('input[type="email"]').fill(EMAIL);
    await page.locator('input[type="password"]').fill(PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 25000 });
    await page.waitForTimeout(1000);

    const token = await page.evaluate(() => localStorage.getItem('atlas_token'));
    const legacyFlag = await page.evaluate(() => localStorage.getItem('atlas_logged_in'));

    record('stores a structurally valid JWT', isStructurallyValidJwt(token));
    record('does not write atlas_logged_in', legacyFlag === null);
    record('calls /auth/login exactly once', loginCalls.count === 1, `got ${loginCalls.count}`);
  } catch (err) {
    record('clean browser login', false, err.message);
  } finally {
    await context.close();
  }
}

async function scenarioSeededToken(browser) {
  console.log('\n🧪 Scenario 2: valid pre-seeded JWT');
  const { context, page } = await newPage(browser);
  try {
    const token = await getRealJwt();
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await page.evaluate((jwt) => localStorage.setItem('atlas_token', jwt), token);
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'networkidle' });
    await page.waitForURL('**/dashboard', { timeout: 15000 });
    const current = await page.evaluate(() => localStorage.getItem('atlas_token'));
    record('valid session reaches workspace', current === token);
  } catch (err) {
    record('valid pre-seeded JWT', false, err.message);
  } finally {
    await context.close();
  }
}

async function scenarioInvalidToken(browser) {
  console.log('\n🧪 Scenario 3: invalid JWT is rejected without automatic re-auth');
  const { context, page, loginCalls } = await newPage(browser);
  try {
    const token = corruptSignature(await getRealJwt());
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await page.evaluate((jwt) => localStorage.setItem('atlas_token', jwt), token);
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'networkidle' });
    await page.waitForURL('**/login', { timeout: 15000 });

    const after = await page.evaluate(() => localStorage.getItem('atlas_token'));
    record('invalid token redirects to /login', true);
    record('invalid token is cleared', after === null);
    record('no automatic re-auth attempt', loginCalls.count === 0, `got ${loginCalls.count}`);
  } catch (err) {
    record('invalid JWT rejection', false, err.message);
  } finally {
    await context.close();
  }
}

async function scenarioSignOut(browser) {
  console.log('\n🧪 Scenario 4: sign out clears the session');
  const { context, page } = await newPage(browser);
  try {
    const token = await getRealJwt();
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await page.evaluate((jwt) => localStorage.setItem('atlas_token', jwt), token);
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'networkidle' });
    await page.waitForURL('**/dashboard', { timeout: 15000 });

    await page.getByRole('button', { name: /sign out/i }).click();
    await page.waitForURL(`${BASE_URL}/`, { timeout: 10000 });

    const after = await page.evaluate(() => localStorage.getItem('atlas_token'));
    record('sign out clears atlas_token', after === null);
    record('sign out leaves the workspace', !page.url().includes('/dashboard'));
  } catch (err) {
    record('sign out', false, err.message);
  } finally {
    await context.close();
  }
}

async function main() {
  if (!EMAIL || !PASSWORD) {
    console.error('Set ATLAS_E2E_EMAIL and ATLAS_E2E_PASSWORD to a real Atlas account.');
    process.exit(2);
  }

  console.log('='.repeat(60));
  console.log('🛡️  ATLAS AUTH SESSION REGRESSION SUITE');
  console.log('='.repeat(60));

  if (!(await waitForBackend())) {
    console.error('❌ Backend is not responding.');
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  try {
    await scenarioCleanLogin(browser);
    await scenarioSeededToken(browser);
    await scenarioInvalidToken(browser);
    await scenarioSignOut(browser);
  } finally {
    await browser.close();
  }

  const failed = results.filter((r) => !r.passed);
  console.log('\n' + '='.repeat(60));
  console.log(`SUMMARY: ${results.length - failed.length}/${results.length} checks passed`);
  console.log('='.repeat(60));
  if (failed.length > 0) {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error('Suite fatal exception:', err);
  process.exit(1);
});
