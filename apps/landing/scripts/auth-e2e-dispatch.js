import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function runAuthE2EDispatchTest() {
  console.log('==================================================');
  console.log('🧪 REAL BROWSER AUTH & DISPATCH E2E REGRESSION TEST');
  console.log('   Target: http://localhost:5173');
  console.log('   Backend: http://127.0.0.1:8000');
  console.log('==================================================');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const networkLog = [];
  const status401Errors = [];

  page.on('response', (res) => {
    const status = res.status();
    const url = res.url();
    networkLog.push({ url, status, method: res.request().method() });
    if (status === 401) {
      status401Errors.push({ url, method: res.request().method() });
      console.error(`❌ HTTP 401 UNAUTHORIZED DETECTED: ${res.request().method()} ${url}`);
    }
  });

  // 1. Open login page
  console.log('1. Navigating to http://localhost:5173/login...');
  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });

  // 2. Perform Login via form
  console.log('2. Entering credentials for demo@atlas.val...');
  await page.fill('input[type="text"], input[type="email"], input[name="identifier"]', 'demo@atlas.val');
  await page.fill('input[type="password"]', 'password123');
  await page.click('button[type="submit"]');

  await page.waitForTimeout(1500);

  // Verify JWT token is present in localStorage
  const storedToken = await page.evaluate(() => localStorage.getItem('atlas_token'));
  console.log(`3. LocalStorage JWT Token Retrieved: ${Boolean(storedToken)}`);

  if (!storedToken) {
    console.error('❌ FAIL: No JWT access token stored in localStorage after login!');
    process.exit(1);
  }

  // 4. Navigate to New Evaluation
  console.log('4. Navigating to http://localhost:5173/dashboard/evaluations/new...');
  await page.goto('http://localhost:5173/dashboard/evaluations/new', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // 5. Submit Execution Dispatch
  console.log('5. Clicking Run Evaluation button...');
  const submitBtn = page.locator('#run-eval-submit-btn');
  await submitBtn.waitFor({ state: 'visible', timeout: 5000 });
  
  // Intercept dispatch POST response
  const dispatchResponsePromise = page.waitForResponse(
    (res) => res.url().includes('/api/v1/benchmarks/') && res.url().includes('/executions') && res.request().method() === 'POST',
    { timeout: 10000 }
  );

  await submitBtn.click();
  const dispatchRes = await dispatchResponsePromise;
  const dispatchStatus = dispatchRes.status();
  const dispatchBody = await dispatchRes.json();

  console.log(`6. Dispatch HTTP Status Code: ${dispatchStatus}`);
  console.log(`7. Dispatch Execution Payload:`, JSON.stringify(dispatchBody));

  if (dispatchStatus !== 201) {
    console.error(`❌ FAIL: Expected HTTP 201 Created from dispatch, got HTTP ${dispatchStatus}`);
    process.exit(1);
  }

  const executionId = dispatchBody.id;
  console.log(`✅ DISPATCH SUCCESSFUL! Execution ID: ${executionId}`);

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

  if (status401Errors.length > 0) {
    console.error(`❌ FAIL: ${status401Errors.length} HTTP 401 Unauthorized errors occurred during test!`);
    process.exit(1);
  }

  const screenshotPath = path.resolve(__dirname, 'auth_e2e_dispatch_success.png');
  await page.screenshot({ path: screenshotPath, fullPage: true });

  await browser.close();

  console.log('\n==================================================');
  console.log('✨ AUTHENTICATION & EXECUTION DISPATCH TEST PASSED!');
  console.log(`   Execution ID: ${executionId}`);
  console.log(`   HTTP 401 Errors: 0`);
  console.log('==================================================\n');
}

runAuthE2EDispatchTest().catch((err) => {
  console.error('Auth E2E Test Exception:', err);
  process.exit(1);
});
