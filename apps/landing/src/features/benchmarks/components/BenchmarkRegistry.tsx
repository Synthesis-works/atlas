import { Database } from 'lucide-react';
import { AtlasBenchmarkCatalog } from './catalog/AtlasBenchmarkCatalog';

export const BenchmarkRegistry: React.FC = () => {
  return (
    <div className="liquid-glass-card rounded-2xl border border-white/10 p-5 space-y-4 flex flex-col flex-1 min-h-0">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
        <div>
          <div className="flex items-center gap-1.5 font-mono text-xs text-white/40 uppercase tracking-wider mb-0.5">
            <Database className="w-3.5 h-3.5 text-accent" />
            <span>Step 5: Manage — Operational Registry Table</span>
          </div>
          <h3 className="text-sm font-semibold text-white tracking-tight">Registered Evaluation Suites</h3>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto min-h-0">
        <AtlasBenchmarkCatalog />
      </div>
    </div>
  );
};

export default BenchmarkRegistry;

