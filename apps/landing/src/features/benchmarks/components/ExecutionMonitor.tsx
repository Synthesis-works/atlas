import React from 'react';
import { Terminal } from '@/shared/components';

interface ExecutionMonitorProps {
  logs: string[];
}

export const ExecutionMonitor: React.FC<ExecutionMonitorProps> = ({ logs }) => {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-white tracking-tight">Live Execution Monitor</h3>
        <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Streaming Log Output
        </span>
      </div>
      <Terminal title="Atlas Execution Harness — Terminal Output" logs={logs} />
    </div>
  );
};

export default ExecutionMonitor;
