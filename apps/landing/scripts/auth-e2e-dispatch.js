import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function runScenario(browser, scenarioName, setupFn) {
  console.log(`\n==================================================`);
  console.log(`🧪 SCENARIO: ${scenarioName}`);
  console.log(`==================================================`);

  const context = await browser.newContext();
  const page = await context.newPage();

  const networkLog = [];
  const status401Errors = [];

  page.on('response', (res) => {
    const status = res.status();
    const url = res.url();
    networkLog.push({ url, status, method: res.request().method() });
    if (status === 401 && !url.includes('/auth/login')) {
      status401Errors.push({ url, method: res.request().method() });
      console.error(`❌ HTTP 401 UNAUTHORIZED DETECTED: ${res.request().method()} ${url}`);
    }
  });

  if (setupFn) {
    await setupFn(page);
  }

  // 1. Load app or login
  console.log('1. Navigating to http://localhost:5173/login...');
  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });

  // 2. Perform Login if needed
  const tokenInStorage = await page.evaluate(() => localStorage.getItem('atlas_token'));
  if (!tokenInStorage || tokenInStorage.includes('expired')) {
    console.log('2. Entering credentials for demo@atlas.val...');
    await page.fill('input[type="text"], input[type="email"], input[name="identifier"]', 'demo@atlas.val');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(1500);
  }

  // Verify JWT token is present in localStorage
  const storedToken = await page.evaluate(() => localStorage.getItem('atlas_token'));
  console.log(`3. LocalStorage JWT Token Valid: ${Boolean(storedToken && !storedToken.includes('expired'))}`);

  if (!storedToken) {
    console.error('❌ FAIL: No JWT access token stored in localStorage!');
    await context.close();
    return false;
  }

  // 4. Navigate to New Evaluation
  console.log('4. Navigating to http://localhost:5173/dashboard/evaluations/new...');
  await page.goto('http://localhost:5173/dashboard/evaluations/new', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // 5. Submit Execution Dispatch
  console.log('5. Clicking Run Evaluation button...');
  const submitBtn = page.locator('#run-eval-submit-btn');
  await submitBtn.waitFor({ state: 'visible', timeout: 5000 });

  const dispatchResponsePromise = page.waitForResponse(
    (res) => res.url().includes('/api/v1/benchmarks/') && res.url().includes('/executions') && res.request().method() === 'POST',
    { timeout: 10000 }
  );

  await submitBtn.click();
  const dispatchRes = await dispatchResponsePromise;
  const dispatchStatus = dispatchRes.status();
  const dispatchBody = await dispatchRes.json();

  console.log(`6. Dispatch HTTP Status Code: ${dispatchStatus}`);
  console.log(`7. Dispatch Execution Payload ID: ${dispatchBody.id}`);

  if (dispatchStatus !== 201) {
    console.error(`❌ FAIL: Expected HTTP 201 Created from dispatch, got HTTP ${dispatchStatus}`);
    await context.close();
    return false;
  }

  const executionId = dispatchBody.id;

  // 8. Poll for completion using authenticated requests
  console.log('8. Polling execution status until COMPLETED...');
  let completed = false;
  for (let attempt = 1; attempt <= 15; attempt++) {
    await page.waitForTimeout(1000);
    const pollStatus = await page.evaluate(async (id) => {
      const token = localStorage.getItem('atlas_token');
      const res = await fetch(`http://127.0.0.1:8000/api/v1/executions/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) return `HTTP_${res.status}`;
      const data = await res.json();
      return data.status || data.data?.status;
    }, executionId);

    console.log(`  [Poll ${attempt}] Status: ${pollStatus}`);
    if (pollStatus === 'Completed' || pollStatus === 'COMPLETED') {
      completed = true;
      break;
    }
  }

  if (!completed) {
    console.error('❌ FAIL: Execution did not reach COMPLETED state!');
    await context.close();
    return false;
  }

  if (status401Errors.length > 0) {
    console.error(`❌ FAIL: ${status401Errors.length} HTTP 401 Unauthorized errors occurred!`);
    await context.close();
    return false;
  }

  await context.close();
  console.log(`✅ SCENARIO PASSED: ${scenarioName} (0 HTTP 401s, Execution ID: ${executionId})`);
  return true;
}

async function runAllE2EScenarios() {
  console.log('==================================================');
  console.log('🛡️ ATLAS HARDENED AUTHENTICATION & DISPATCH E2E SUITE');
  console.log('==================================================');

  const browser = await chromium.launch({ headless: true });

  // 1. Clean Browser Context
  const res1 = await runScenario(browser, '1. Clean Browser Scratch Context', async (page) => {
    await page.goto('http://localhost:5173/login');
    await page.evaluate(() => localStorage.clear());
  });

  // 2. Returning User Session
  const res2 = await runScenario(browser, '2. Returning User Valid Session', async (page) => {
    await page.goto('http://localhost:5173/login');
    await page.evaluate(async () => {
      const res = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'demo@atlas.val', password: 'password123' })
      });
      const data = await res.json();
      const token = data.data?.access_token || data.access_token;
      localStorage.setItem('atlas_token', token);
      localStorage.setItem('atlas_logged_in', 'true');
    });
  });

  // 3. Expired Token Recovery
  const res3 = await runScenario(browser, '3. Expired Token Automatic Recovery', async (page) => {
    await page.goto('http://localhost:5173/login');
    await page.evaluate(() => {
      // Set an explicitly expired JWT in localStorage
      localStorage.setItem('atlas_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDIiLCJleHAiOjEwMDAwMDAwMDB9.invalid_signature_expired');
      localStorage.setItem('atlas_logged_in', 'true');
    });
  });

  await browser.close();

  console.log('\n==================================================');
  console.log('📊 HARDENED SUITE SUMMARY');
  console.log('==================================================');
  console.log(`Scenario 1 (Clean Browser Scratch):    ${res1 ? '✅ PASSED' : '❌ FAILED'}`);
  console.log(`Scenario 2 (Returning Valid Session):  ${res2 ? '✅ PASSED' : '❌ FAILED'}`);
  console.log(`Scenario 3 (Expired Token Recovery):   ${res3 ? '✅ PASSED' : '❌ FAILED'}`);

  if (!res1 || !res2 || !res3) {
    console.error('\n❌ REGRESSION SUITE FAILED!');
    process.exit(1);
  }

  console.log('\n✨ ALL HARDENED AUTHENTICATION & DISPATCH E2E SCENARIOS PASSED PERFECTLY!\n');
}

runAllE2EScenarios().catch((err) => {
  console.error('Hardened Suite Exception:', err);
  process.exit(1);
});
