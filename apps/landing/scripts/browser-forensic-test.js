import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function runForensicAudit() {
  console.log('==================================================');
  console.log('🚀 STARTING PLAYWRIGHT REAL BROWSER FORENSIC AUDIT');
  console.log('==================================================');

  const browser = await chromium.launch({ headless: true });
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

  const targetUrl = 'http://127.0.0.1:5173/dashboard/evaluations/new';
  console.log(`Navigating Chromium to: ${targetUrl}`);

  try {
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle', timeout: 15000 });
    await page.evaluate(() => {
      localStorage.setItem('atlas_logged_in', 'true');
      localStorage.setItem('atlas_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDIiLCJtZW1iZXJzaGlwX2lkIjpudWxsLCJvcmdhbml6YXRpb25faWQiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDEiLCJleHAiOjE3ODY3NzAxMDksImlhdCI6MTc4NjYxNDE0OSwianRpIjoiNTZkNzU1ZDUtNzhjZS00YzE1LWE5MDItMGI1ZjVjODcxMTRiIn0.pho6L20Aubonc8tn-gGj-s3vOfwlKuSHpY8HjPpVvlU');
    });
    await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 15000 });
  } catch (gotoErr) {
    console.warn(`[Warning] Navigation timeout/issue: ${gotoErr.message}`);
  }

  // Wait extra 2s to allow React lazy suspense to settle
  await page.waitForTimeout(2000);

  const screenshotPath = path.resolve(__dirname, 'browser_forensic_screenshot.png');
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const pageUrl = page.url();
  const pageTitle = await page.title();
  const bodyText = await page.evaluate(() => document.body.innerText);
  const bodyHtmlLen = await page.evaluate(() => document.body.innerHTML.length);
  const rootHtmlLen = await page.evaluate(() => document.querySelector('#root')?.innerHTML.length || 0);
  const rootChildrenCount = await page.evaluate(() => document.querySelector('#root')?.children.length || 0);
  const canonicalMarker = await page.evaluate(() => {
    const el = document.querySelector('[data-canonical-marker]');
    return el ? el.getAttribute('data-canonical-marker') : null;
  });

  const computedStyles = await page.evaluate(() => {
    const rootEl = document.querySelector('#root');
    const firstChild = rootEl?.firstElementChild;
    const bodyStyle = window.getComputedStyle(document.body);
    const rootStyle = rootEl ? window.getComputedStyle(rootEl) : null;
    const childStyle = firstChild ? window.getComputedStyle(firstChild) : null;

    return {
      body: {
        display: bodyStyle.display,
        visibility: bodyStyle.visibility,
        opacity: bodyStyle.opacity,
        backgroundColor: bodyStyle.backgroundColor,
        color: bodyStyle.color,
      },
      root: rootStyle ? {
        display: rootStyle.display,
        visibility: rootStyle.visibility,
        opacity: rootStyle.opacity,
        height: rootStyle.height,
        width: rootStyle.width,
        overflow: rootStyle.overflow,
      } : null,
      topReactChild: childStyle ? {
        display: childStyle.display,
        visibility: childStyle.visibility,
        opacity: childStyle.opacity,
        position: childStyle.position,
        zIndex: childStyle.zIndex,
      } : null,
    };
  });

  const rootInnerHtmlSnippet = await page.evaluate(() => {
    const root = document.querySelector('#root');
    return root ? root.innerHTML.substring(0, 300) : 'NO_ROOT';
  });

  console.log('\n--- BROWSER DOM STATE ---');
  console.log(`Page URL: ${pageUrl}`);
  console.log(`Page Title: ${pageTitle}`);
  console.log(`Body InnerText Length: ${bodyText.length}`);
  console.log(`Body InnerHTML Length: ${bodyHtmlLen}`);
  console.log(`Root InnerHTML Length: ${rootHtmlLen}`);
  console.log(`Root Children Count: ${rootChildrenCount}`);
  console.log(`Canonical Marker: ${canonicalMarker}`);
  console.log(`Root InnerHTML Snippet: ${rootInnerHtmlSnippet}`);

  console.log('\n--- COMPUTED STYLES ---');
  console.log(JSON.stringify(computedStyles, null, 2));

  console.log('\n--- CHRONOLOGICAL BROWSER CONSOLE MESSAGES ---');
  if (consoleLogs.length === 0) {
    console.log('No console messages.');
  } else {
    consoleLogs.forEach((log, i) => console.log(`[${i + 1}] [${log.type}] ${log.text}`));
  }

  console.log('\n--- PAGE ERRORS (JAVASCRIPT EXCEPTIONS) ---');
  if (pageErrors.length === 0) {
    console.log('No JS page errors.');
  } else {
    pageErrors.forEach((err, i) => {
      console.log(`[${i + 1}] ${err.name}: ${err.message}`);
      if (err.stack) console.log(err.stack);
    });
  }

  console.log('\n--- REQUEST FAILURES ---');
  if (requestFailures.length === 0) {
    console.log('No request failures.');
  } else {
    requestFailures.forEach((fail, i) => {
      console.log(`[${i + 1}] ${fail.method} ${fail.url} -> ${fail.failure}`);
    });
  }

  console.log('\n--- JS MODULE NETWORK RESPONSES ---');
  const jsRequests = networkRequests.filter(r => r.url.endsWith('.js') || r.url.endsWith('.tsx') || r.url.includes('/src/'));
  jsRequests.forEach((req, i) => {
    console.log(`[${i + 1}] ${req.status} ${req.url} (${req.contentType})`);
  });

  console.log(`\nScreenshot saved to: ${screenshotPath}`);

  await browser.close();
  console.log('==================================================');
}

runForensicAudit().catch(err => {
  console.error('Forensic Audit Error:', err);
  process.exit(1);
});
