import { execSync } from 'child_process';
import path from 'path';

const PORT = 8000;
const CURRENT_DIR = path.resolve(process.cwd());

console.log('==================================================');
console.log('🛡️ ATLAS BACKEND PORT SECURITY GUARD');
console.log('==================================================');

try {
  let netstatOutput = '';
  try {
    netstatOutput = execSync(`netstat -ano`, { encoding: 'utf-8' });
  } catch (e) {
    console.error('Failed to run netstat:', e.message);
  }

  const lines = netstatOutput.split('\n');
  const listeningPids = new Set();

  for (const line of lines) {
    if ((line.includes(':8000 ') || line.includes(':8000\t')) && (line.includes('LISTENING') || line.includes('ESTABLISHED'))) {
      const parts = line.trim().split(/\s+/);
      const pid = parts[parts.length - 1];
      if (pid && !isNaN(parseInt(pid, 10)) && pid !== '0') {
        listeningPids.add(pid);
      }
    }
  }

  console.log(`[Atlas Backend Guard] Discovered ${listeningPids.size} listener PIDs on port 8000.`);

  for (const pid of listeningPids) {
    let procInfo = '';
    try {
      procInfo = execSync(
        `powershell -Command "Get-CimInstance Win32_Process -Filter \\"ProcessId = ${pid}\\" | Select-Object -ExpandProperty CommandLine"`,
        { encoding: 'utf-8' }
      ).trim();
    } catch (e) {
      procInfo = 'Unknown Process';
    }

    const isCurrentWorktree = procInfo.includes('wire_real_llm_adapter');

    if (!isCurrentWorktree) {
      console.error(`\n❌ FOREIGN / STALE BACKEND PROCESS DETECTED ON PORT 8000:`);
      console.error(`  - PID: ${pid}`);
      console.error(`  - Command: ${procInfo}`);
      console.error(`  - Action: Auto-terminating foreign process...`);
      try {
        execSync(`powershell -Command "Stop-Process -Id ${pid} -Force"`);
        console.log(`  - Result: Successfully killed PID ${pid}.\n`);
      } catch (killErr) {
        console.error(`  - Result: FAILED to kill PID ${pid}: ${killErr.message}`);
        console.error('❌ CANNOT CONTINUE. Exiting to prevent backend port collision.');
        process.exit(1);
      }
    } else {
      console.log(`  - PID ${pid}: Valid canonical backend process in wire_real_llm_adapter.`);
    }
  }

  console.log('✅ Port 8000 audit complete. Canonical backend API launching...\n');
} catch (err) {
  console.error('[Atlas Backend Guard] Exception during port audit:', err.message);
  process.exit(1);
}
