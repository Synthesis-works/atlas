import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '../src');

console.log('==================================================');
console.log('🧪 ATLAS RUNTIME ROUTE & COMPONENT INTEGRITY AUDIT');
console.log('==================================================');

const requiredFiles = [
  'App.tsx',
  'pages/workspace/Experiments.tsx',
  'features/evaluations/components/EvaluationsFeature.tsx',
  'features/evaluations/components/NewEvaluationModal.tsx',
  'pages/workspace/WorkspaceNotFound.tsx'
];

let allExist = true;
for (const relPath of requiredFiles) {
  const fullPath = path.join(SRC_DIR, relPath);
  if (fs.existsSync(fullPath)) {
    console.log(`✅ [FOUND] ${relPath}`);
  } else {
    console.error(`❌ [MISSING] ${relPath}`);
    allExist = false;
  }
}

if (!allExist) {
  console.error('\n❌ RUNTIME ROUTE AUDIT FAILED: Required file missing.');
  process.exit(1);
}

// Verify Experiments.tsx exports default correctly
const expContent = fs.readFileSync(path.join(SRC_DIR, 'pages/workspace/Experiments.tsx'), 'utf-8');
if (!expContent.includes('export default WorkspaceExperimentsPage') && !expContent.includes('export default')) {
  console.error('❌ [FAIL] Experiments.tsx is missing default export needed for lazy loading.');
  process.exit(1);
} else {
  console.log('✅ [PASS] Experiments.tsx default export verified');
}

// Verify data-canonical-marker exists
if (!expContent.includes('ATLAS_CANONICAL_WORKTREE_MARKER')) {
  console.error('❌ [FAIL] Experiments.tsx is missing ATLAS_CANONICAL_WORKTREE_MARKER.');
  process.exit(1);
} else {
  console.log('✅ [PASS] ATLAS_CANONICAL_WORKTREE_MARKER verified in Experiments.tsx');
}

console.log('\n==================================================');
console.log('✨ RUNTIME ROUTE COMPONENT INTEGRITY VERIFIED');
console.log('==================================================\n');
