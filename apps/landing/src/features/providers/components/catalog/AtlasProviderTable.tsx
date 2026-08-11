import { ArrowDown, ArrowUp, ShieldCheck } from "lucide-react";
import type { useProviderCatalog } from "../../hooks/useProviderCatalog";

export function AtlasProviderTable({ catalog }: { catalog: ReturnType<typeof useProviderCatalog> }) {
  const { 
    rows, 
    rawVisibleIds, 
    selectedIds, 
    sort, 
    handleSelect, 
    handleSelectAll, 
    handleOpenPreview, 
    setSort 
  } = catalog;

  const allSelected = rawVisibleIds.length > 0 && rawVisibleIds.every(id => selectedIds.includes(id));
  const someSelected = rawVisibleIds.some(id => selectedIds.includes(id)) && !allSelected;

  const handleSort = (field: typeof sort.field) => {
    if (sort.field === field) {
      setSort({ field, direction: sort.direction === 'asc' ? 'desc' : 'asc' });
    } else {
      setSort({ field, direction: 'desc' });
    }
  };

  const SortIcon = ({ field }: { field: typeof sort.field }) => {
    if (sort.field !== field) return null;
    return sort.direction === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />;
  };

  const StatusBadge = ({ status }: { status: string }) => {
    switch (status) {
      case 'operational': return <span className="text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full text-xs border border-emerald-400/20">Operational</span>;
      case 'degraded': return <span className="text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded-full text-xs border border-yellow-400/20">Degraded</span>;
      case 'outage': return <span className="text-red-400 bg-red-400/10 px-2 py-0.5 rounded-full text-xs border border-red-400/20">Outage</span>;
      case 'maintenance': return <span className="text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded-full text-xs border border-blue-400/20">Maintenance</span>;
      default: return <span className="text-slate-400 bg-slate-400/10 px-2 py-0.5 rounded-full text-xs border border-slate-400/20">Unknown</span>;
    }
  };

  return (
    <div className="w-full text-sm">
      <div className="grid grid-cols-[48px_minmax(200px,1fr)_120px_100px_100px_100px_1fr] items-center px-4 py-3 border-b border-white/5 bg-white/[0.02] text-white/50 font-medium">
        <div className="flex items-center justify-center">
          <input 
            type="checkbox"
            className="rounded border-white/20 bg-white/5 text-indigo-500 focus:ring-indigo-500/50"
            checked={allSelected}
            ref={input => { if (input) input.indeterminate = someSelected; }}
            onChange={() => handleSelectAll(rawVisibleIds)}
          />
        </div>
        <div className="cursor-pointer hover:text-white transition-colors flex items-center gap-1" onClick={() => handleSort('name')}>
          Name <SortIcon field="name" />
        </div>
        <div>Status</div>
        <div className="cursor-pointer hover:text-white transition-colors flex items-center gap-1" onClick={() => handleSort('modelsCount')}>
          Models <SortIcon field="modelsCount" />
        </div>
        <div className="cursor-pointer hover:text-white transition-colors flex items-center gap-1" onClick={() => handleSort('averageLatencyMs')}>
          Latency <SortIcon field="averageLatencyMs" />
        </div>
        <div className="cursor-pointer hover:text-white transition-colors flex items-center gap-1" onClick={() => handleSort('uptimePercentage')}>
          Uptime <SortIcon field="uptimePercentage" />
        </div>
        <div>Regions</div>
      </div>

      <div className="flex flex-col">
        {rows.map((row) => {
          const isSelected = selectedIds.includes(row.id);
          return (
            <div 
              key={row.id}
              onClick={() => handleOpenPreview(row.id)}
              className={`
                grid grid-cols-[48px_minmax(200px,1fr)_120px_100px_100px_100px_1fr] items-center px-4 py-3 
                border-b border-white/5 cursor-pointer transition-colors
                ${isSelected ? 'bg-indigo-500/10' : 'hover:bg-white/[0.02]'}
              `}
            >
              <div 
                className="flex items-center justify-center"
                onClick={(e) => { e.stopPropagation(); handleSelect(row.id, true); }}
              >
                <input 
                  type="checkbox"
                  className="rounded border-white/20 bg-white/5 text-indigo-500 focus:ring-indigo-500/50"
                  checked={isSelected}
                  onChange={() => {}}
                />
              </div>
              
              <div className="flex flex-col pr-4">
                <div className="font-medium text-white group-hover:text-indigo-300 transition-colors truncate">
                  {row.name}
                </div>
                <div className="text-xs text-white/40 capitalize">{row.tier}</div>
              </div>
              
              <div><StatusBadge status={row.status} /></div>
              
              <div className="text-white/70">{row.modelsCount}</div>
              
              <div className="text-white/70">{row.averageLatencyMs}ms</div>
              
              <div className="text-white/70 flex items-center gap-1.5">
                {row.uptimePercentage}%
                {row.uptimePercentage >= 99.9 && <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />}
              </div>
              
              <div className="flex gap-1.5 flex-wrap">
                {row.regions.map(r => (
                  <span key={r} className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-white/50 border border-white/5">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
