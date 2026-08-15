import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function auditUrl(browser, targetUrl, screenshotFilename) {
  console.log(`\n--------------------------------------------------`);
  console.log(`🌐 AUDITING ENDPOINT: ${targetUrl}`);
  console.log(`--------------------------------------------------`);

  const context = await browser.newContext();
  const page = await context.newPage();

  const consoleLogs = [];
  const pageErrors = [];
  const requestFailures = [];
  const networkRequests = [];

  page.on('console', (msg) => {
    consoleLogs.push({ type: msg.type(), text: msg.text() });
  });

  page.on('pageerror', (err) => {
    pageErrors.push({ name: err.name, message: err.message, stack: err.stack });
  });

  page.on('requestfailed', (req) => {
    requestFailures.push({
      url: req.url(),
      method: req.method(),
      failure: req.failure()?.errorText || 'Unknown failure',
    });
  });

  page.on('response', (res) => {
    networkRequests.push({
      url: res.url(),
      status: res.status(),
      contentType: res.headers()['content-type'] || '',
    });
  });

  const originHost = new URL(targetUrl).origin;

  try {
    await page.goto(`${originHost}/login`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.evaluate(() => {
      localStorage.setItem('atlas_logged_in', 'true');
      localStorage.setItem('atlas_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDIiLCJtZW1iZXJzaGlwX2lkIjpudWxsLCJvcmdhbml6YXRpb25faWQiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDEiLCJleHAiOjE3ODY3NzAxMDksImlhdCI6MTc4NjYxNDE0OSwianRpIjoiNTZkNzU1ZDUtNzhjZS00YzE1LWE5MDItMGI1ZjVjODcxMTRiIn0.pho6L20Aubonc8tn-gGj-s3vOfwlKuSHpY8HjPpVvlU');
    });
    await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 15000 });
  } catch (gotoErr) {
    console.warn(`[Warning] Navigation issue for ${targetUrl}: ${gotoErr.message}`);
  }

  await page.waitForTimeout(2000);

  const screenshotPath = path.resolve(__dirname, screenshotFilename);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const finalUrl = page.url();
  const pageTitle = await page.title();
  const bodyText = await page.evaluate(() => document.body.innerText);
  const bodyHtmlLen = await page.evaluate(() => document.body.innerHTML.length);
  const rootHtmlLen = await page.evaluate(() => document.querySelector('#root')?.innerHTML.length || 0);
  const rootChildrenCount = await page.evaluate(() => document.querySelector('#root')?.children.length || 0);
  const canonicalMarker = await page.evaluate(() => {
    const el = document.querySelector('[data-canonical-marker]');
    return el ? el.getAttribute('data-canonical-marker') : null;
  });

  console.log(`Final Page URL: ${finalUrl}`);
  console.log(`Page Title: ${pageTitle}`);
  console.log(`Body InnerText Length: ${bodyText.length}`);
  console.log(`Body InnerHTML Length: ${bodyHtmlLen}`);
  console.log(`Root InnerHTML Length: ${rootHtmlLen}`);
  console.log(`Root Children Count: ${rootChildrenCount}`);
  console.log(`Canonical Marker: ${canonicalMarker}`);
  console.log(`Screenshot Saved: ${screenshotPath}`);

  if (consoleLogs.length > 0) {
    console.log(`Console Messages (${consoleLogs.length}):`);
    consoleLogs.forEach((l, i) => console.log(`  [${i + 1}] [${l.type}] ${l.text}`));
  }
  if (pageErrors.length > 0) {
    console.error(`❌ Page Errors (${pageErrors.length}):`);
    pageErrors.forEach((e, i) => console.error(`  [${i + 1}] ${e.name}: ${e.message}`));
  }
  if (requestFailures.length > 0) {
    console.error(`❌ Request Failures (${requestFailures.length}):`);
    requestFailures.forEach((f, i) => console.error(`  [${i + 1}] ${f.method} ${f.url} -> ${f.failure}`));
  }

  await context.close();

  return {
    targetUrl,
    finalUrl,
    rootHtmlLen,
    rootChildrenCount,
    canonicalMarker,
    pageErrorsCount: pageErrors.length,
    requestFailuresCount: requestFailures.length,
  };
}

async function runForensicAudit() {
  console.log('==================================================');
  console.log('🚀 DUAL ORIGIN PLAYWRIGHT BROWSER FORENSIC AUDIT');
  console.log('   Testing both http://localhost:5173 AND http://127.0.0.1:5173');
  console.log('==================================================');

  const browser = await chromium.launch({ headless: true });

  const localhostRes = await auditUrl(
    browser,
    'http://localhost:5173/dashboard/evaluations/new',
    'screenshot_localhost.png'
  );

  const ipRes = await auditUrl(
    browser,
    'http://127.0.0.1:5173/dashboard/evaluations/new',
    'screenshot_127.png'
  );

  await browser.close();

  console.log('\n==================================================');
  console.log('📊 DUAL ORIGIN FORENSIC AUDIT SUMMARY');
  console.log('==================================================');
  console.log(`http://localhost:5173 -> Marker: ${localhostRes.canonicalMarker} | RootLen: ${localhostRes.rootHtmlLen}`);
  console.log(`http://127.0.0.1:5173 -> Marker: ${ipRes.canonicalMarker} | RootLen: ${ipRes.rootHtmlLen}`);

  let failed = false;

  if (localhostRes.canonicalMarker !== 'ATLAS_CANONICAL_WORKTREE_MARKER') {
    console.error('❌ FAIL: http://localhost:5173 is missing ATLAS_CANONICAL_WORKTREE_MARKER!');
    failed = true;
  } else {
    console.log('✅ PASS: http://localhost:5173 rendered canonical worktree!');
  }

  if (ipRes.canonicalMarker !== 'ATLAS_CANONICAL_WORKTREE_MARKER') {
    console.error('❌ FAIL: http://127.0.0.1:5173 is missing ATLAS_CANONICAL_WORKTREE_MARKER!');
    failed = true;
  } else {
    console.log('✅ PASS: http://127.0.0.1:5173 rendered canonical worktree!');
  }

  if (failed) {
    console.error('\n❌ AUDIT FAILED: Origin divergence detected!');
    process.exit(1);
  }

  console.log('\n✨ DUAL ORIGIN AUDIT PASSED PERFECTLY WITH ZERO DIVERGENCE!\n');
}

runForensicAudit().catch((err) => {
  console.error('Forensic Audit Error:', err);
  process.exit(1);
});
