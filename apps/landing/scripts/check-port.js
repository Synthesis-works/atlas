import { execSync } from 'child_process';
import path from 'path';

const PORT = 5173;
const CURRENT_DIR = path.resolve(process.cwd());

try {
  let netstatOutput = '';
  try {
    netstatOutput = execSync(`netstat -ano`, { encoding: 'utf-8' });
  } catch (e) {
    // Ignore error
  }

  const lines = netstatOutput.split('\n');
  let occupyingPid = null;

  for (const line of lines) {
    if (line.includes(`:5173`) && line.includes('LISTENING')) {
      const parts = line.trim().split(/\s+/);
      occupyingPid = parts[parts.length - 1];
      break;
    }
  }

  if (occupyingPid) {
    let procInfo = '';
    try {
      procInfo = execSync(
        `powershell -Command "Get-CimInstance Win32_Process -Filter \\"ProcessId = ${occupyingPid}\\" | Select-Object -ExpandProperty CommandLine"`,
        { encoding: 'utf-8' }
      ).trim();
    } catch (e) {
      procInfo = 'Unknown Process';
    }

    const isCurrentWorktree = procInfo.includes('wire_real_llm_adapter');

    if (!isCurrentWorktree) {
      console.error('\n==================================================');
      console.error('❌ PORT 5173 IS OCCUPIED BY ANOTHER PROJECT');
      console.error('==================================================');
      console.error(`Occupying Process PID: ${occupyingPid}`);
      console.error(`Command Line: ${procInfo}`);
      console.error(`Current Worktree: ${CURRENT_DIR}`);
      console.error('\nPlease terminate the conflicting process on port 5173 before launching Atlas.\n');
      process.exit(1);
    } else {
      console.log(`\n[Atlas Guard] Port 5173 is already in use by active process (PID ${occupyingPid}) in this worktree.\n`);
      process.exit(1);
    }
  } else {
    console.log('[Atlas Guard] Port 5173 is free. Starting canonical dev server on 127.0.0.1:5173...');
  }
} catch (err) {
  // If check fails, allow execution
}
