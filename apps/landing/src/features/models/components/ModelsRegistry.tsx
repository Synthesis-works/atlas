import { AtlasModelCatalog } from './catalog/AtlasModelCatalog';

export function ModelsRegistry() {
  return (
    <div className="liquid-glass-card rounded-2xl overflow-hidden mb-6 border border-white/10 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs font-mono uppercase tracking-wider text-white/40 font-semibold">
            Step 5: Control — Manageable Asset & Fleet Registry
          </div>
          <h3 className="text-sm font-semibold text-white tracking-tight">Active Model Asset Inventory & Control Plane</h3>
        </div>
      </div>
      <AtlasModelCatalog />
    </div>
  );
}

