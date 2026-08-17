import { ArrowDown, ArrowUp, Clock, AlertTriangle } from "lucide-react";
import type { useExperimentCatalog } from "../../hooks/useExperimentCatalog";
import type { ExperimentStatus } from "../../types/catalog";

export function AtlasExperimentTable({ catalog }: { catalog: ReturnType<typeof useExperimentCatalog> }) {
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

  const StatusBadge = ({ status }: { status: ExperimentStatus }) => {
    switch (status) {
      case 'Queued': return <span className="text-white/60 bg-white/5 px-2 py-0.5 rounded text-xs border border-white/10 font-medium">Queued</span>;
      case 'Running': return <span className="text-indigo-400 bg-indigo-400/10 px-2 py-0.5 rounded text-xs border border-indigo-400/20 font-medium animate-pulse">Running</span>;
      case 'Completed': return <span className="text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded text-xs border border-emerald-400/20 font-medium">Completed</span>;
      case 'Failed': return <span className="text-red-400 bg-red-400/10 px-2 py-0.5 rounded text-xs border border-red-400/20 font-medium">Failed</span>;
      case 'Cancelled': return <span className="text-slate-400 bg-slate-400/10 px-2 py-0.5 rounded text-xs border border-slate-400/20 font-medium">Cancelled</span>;
      default: return null;
    }
  };

  const ProgressBar = ({ row }: { row: typeof rows[0] }) => {
    const isFailed = row.status === 'Failed';
    const isCompleted = row.status === 'Completed';
    const isQueued = row.status === 'Queued';
    
    let barColor = 'bg-indigo-500';
    if (isFailed) barColor = 'bg-red-500';
    if (isCompleted) barColor = 'bg-emerald-500';
    if (isQueued) barColor = 'bg-white/20';

    return (
      <div className="flex flex-col gap-1.5 w-full max-w-[200px]">
        <div className="flex justify-between items-center text-xs">
          {row.progressPercentage !== null ? (
            <span className="font-medium text-white/90">{row.progressPercentage}%</span>
          ) : (
            <span className="font-medium text-white/50">—</span>
          )}
          {row.status === 'Running' && (
            <span className="text-indigo-300 font-medium text-[10px] uppercase tracking-wider">{row.currentStage}</span>
          )}
          {isFailed && (
            <span className="text-red-400 font-medium text-[10px] uppercase tracking-wider flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> {row.currentStage}</span>
          )}
        </div>
        <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden relative">
          {row.progressPercentage !== null ? (
            <div 
              className={`h-full ${barColor} ${row.status === 'Running' ? 'relative overflow-hidden' : 'transition-all duration-500'}`}
              style={{ width: `${Math.max(row.progressPercentage, 2)}%` }}
            >
              {row.status === 'Running' && (
                <div className="absolute inset-0 bg-white/20 w-full animate-[shimmer_1.5s_infinite]" style={{ transform: 'skewX(-20deg) translateX(-150%)' }} />
              )}
            </div>
          ) : row.status === 'Running' || row.status === 'Queued' ? (
            <div className={`h-full ${barColor} w-1/3 animate-[shimmer_1.5s_infinite] relative`} />
          ) : (
            <div className={`h-full ${barColor} w-full opacity-30`} />
          )}
        </div>
        <div className="flex justify-between items-center text-[10px] text-white/40 font-medium">
          <span>{row.stageCountText || 'Processing...'}</span>
          {row.etaText && <span>{row.etaText}</span>}
        </div>
      </div>
    );
  };

  return (
    <div className="w-full text-sm">
      <div className="grid grid-cols-[48px_minmax(250px,1fr)_120px_220px_120px_1fr] items-center px-4 py-3 border-b border-white/5 bg-white/[0.02] text-white/50 font-medium">
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
          Experiment <SortIcon field="name" />
        </div>
        <div>Status</div>
        <div className="cursor-pointer hover:text-white transition-colors flex items-center gap-1" onClick={() => handleSort('progress')}>
          Progress <SortIcon field="progress" />
        </div>
        <div className="cursor-pointer hover:text-white transition-colors flex items-center gap-1" onClick={() => handleSort('queuedAt')}>
          Queued <SortIcon field="queuedAt" />
        </div>
        <div>Tags</div>
      </div>

      <div className="flex flex-col">
        {rows.map((row) => {
          const isSelected = selectedIds.includes(row.id);
          return (
            <div 
              key={row.id}
              onClick={() => handleOpenPreview(row.id)}
              className={`
                grid grid-cols-[48px_minmax(250px,1fr)_120px_220px_120px_1fr] items-center px-4 py-4 
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
                <div className="text-xs text-white/40 mt-1 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  Duration: {row.durationText}
                </div>
              </div>
              
              <div><StatusBadge status={row.status} /></div>
              
              <div className="pr-4"><ProgressBar row={row} /></div>
              
              <div className="text-white/50 text-xs">
                {new Date(row.queuedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                <div className="text-[10px] text-white/30">{new Date(row.queuedAt).toLocaleDateString()}</div>
              </div>
              
              <div className="flex gap-1.5 flex-wrap">
                {row.tags.map(t => (
                  <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-white/50 border border-white/5 capitalize">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes shimmer {
          100% { transform: skewX(-20deg) translateX(200%); }
        }
      `}} />
    </div>
  );
}
