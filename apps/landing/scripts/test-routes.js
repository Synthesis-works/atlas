import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_TSX_PATH = path.resolve(__dirname, '../src/App.tsx');

console.log('==================================================');
console.log('🔍 RUNNING ATLAS PERMANENT ROUTE REGRESSION AUDIT');
console.log('==================================================');
console.log(`Target: ${APP_TSX_PATH}`);

if (!fs.existsSync(APP_TSX_PATH)) {
  console.error(`❌ App.tsx not found at ${APP_TSX_PATH}`);
  process.exit(1);
}

const content = fs.readFileSync(APP_TSX_PATH, 'utf-8');

const REQUIRED_PATTERNS = [
  { name: 'Dashboard parent route', pattern: /<Route\s+path="dashboard"/ },
  { name: 'Evaluations parent route', pattern: /<Route\s+path="evaluations">/ },
  { name: 'Evaluations index route', pattern: /<Route\s+index\s+element=/ },
  { name: 'Evaluations /new route', pattern: /<Route\s+path="new"\s+element=/ },
  { name: 'Evaluations wildcard catch-all', pattern: /<Route\s+path="\*"\s+element=/ },
  { name: 'AppErrorBoundary component', pattern: /class AppErrorBoundary extends Component/ },
  { name: 'WorkspaceNotFound fallback import', pattern: /import\('@\/pages\/workspace\/WorkspaceNotFound'\)/ },
];

let failed = false;

for (const req of REQUIRED_PATTERNS) {
  if (req.pattern.test(content)) {
    console.log(`✅ [PASS] ${req.name}`);
  } else {
    console.error(`❌ [FAIL] Missing required route pattern: ${req.name}`);
    failed = true;
  }
}

if (failed) {
  console.error('\n==================================================');
  console.error('❌ ROUTE REGRESSION AUDIT FAILED');
  console.error('==================================================\n');
  process.exit(1);
} else {
  console.log('\n==================================================');
  console.log('✨ ALL ROUTE REGRESSION CHECKS PASSED SUCCESSFULLY');
  console.log('==================================================\n');
}
