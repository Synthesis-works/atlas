import { useEffect, useRef, useState } from 'react';
import { X, CheckCircle2, Circle, Clock, PlayCircle, XCircle, ChevronRight, Activity, Terminal, AlertTriangle } from 'lucide-react';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';
import type { useExperimentCatalog } from '../../hooks/useExperimentCatalog';
import type { MockExperimentStage, MockExperimentStatus } from '../../mocks/mock';

interface Props {
  catalog: ReturnType<typeof useExperimentCatalog>;
}

export function AtlasExperimentPreview({ catalog }: Props) {
  const { previewModel, handleClosePreview } = catalog;
  
  const activeTab = useWorkspaceInteractionStore(s => s.workspaces['experiments']?.view.activePreviewTab || 'Overview');
  const setActiveTab = useWorkspaceInteractionStore(s => s.setActivePreviewTab);
  const setScrollPosition = useWorkspaceInteractionStore(s => s.setScrollPosition);
  const savedScroll = useWorkspaceInteractionStore(s => s.workspaces['experiments']?.navigation.scrollPosition || 0);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const [hoveredStageId, setHoveredStageId] = useState<string | null>(null);
  const [selectedStageId, setSelectedStageId] = useState<string | null>(null);

  // Restore scroll position
  useEffect(() => {
    if (scrollRef.current && savedScroll > 0) {
      scrollRef.current.scrollTop = savedScroll;
    }
  }, [previewModel?.id]);

  useEffect(() => {
    if (selectedStageId && activeTab === 'Logs') {
      const el = document.getElementById(`log-stage-${selectedStageId}`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [selectedStageId, activeTab]);

  if (!previewModel) return null;

  const handleStageClick = (stageId: string) => {
    setSelectedStageId(stageId);
    setActiveTab('experiments', 'Logs');
  };

  const StatusIcon = ({ status }: { status: MockExperimentStatus }) => {
    switch (status) {
      case 'Queued': return <div className="w-2 h-2 rounded-full bg-white/40" />;
      case 'Running': return <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />;
      case 'Completed': return <div className="w-2 h-2 rounded-full bg-emerald-400" />;
      case 'Failed': return <div className="w-2 h-2 rounded-full bg-red-400" />;
      case 'Cancelled': return <div className="w-2 h-2 rounded-full bg-slate-400" />;
      default: return null;
    }
  };

  const StageIcon = ({ status }: { status: MockExperimentStage['status'] }) => {
    switch (status) {
      case 'completed': return <CheckCircle2 className="w-5 h-5 text-emerald-400" />;
      case 'active': return <PlayCircle className="w-5 h-5 text-indigo-400 fill-indigo-400/20 animate-pulse" />;
      case 'failed': return <XCircle className="w-5 h-5 text-red-400" />;
      case 'skipped': return <Circle className="w-5 h-5 text-white/10" />;
      case 'pending': return <Circle className="w-5 h-5 text-white/20" />;
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0F1117] text-white">
      {/* Header */}
      <div className="px-6 py-5 border-b border-white/5 shrink-0 flex items-start justify-between bg-white/[0.02]">
        <div className="flex-1 pr-4">
          <div className="flex items-center gap-2 mb-1">
            <StatusIcon status={previewModel.status} />
            <h2 className="text-xl font-medium tracking-tight text-white/90 truncate">{previewModel.name}</h2>
          </div>
          <div className="flex items-center gap-2 text-sm text-white/40">
            <span>{previewModel.owner}</span>
            <span>•</span>
            <span>{previewModel.durationText}</span>
          </div>
        </div>
        <button 
          onClick={handleClosePreview}
          className="p-2 -mr-2 rounded-lg text-white/40 hover:text-white hover:bg-white/5 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex px-4 border-b border-white/5 shrink-0 overflow-x-auto hide-scrollbar">
        {['Overview', 'Timeline', 'Metrics', 'Configuration', 'Logs'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab('experiments', tab)}
            className={`
              px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
              ${activeTab === tab 
                ? 'border-indigo-500 text-indigo-400' 
                : 'border-transparent text-white/50 hover:text-white/80'}
            `}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Scrollable Content */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto min-h-0"
        onScroll={(e) => {
          setScrollPosition('experiments', (e.target as HTMLDivElement).scrollTop);
        }}
      >
        <div className="p-6">
          
          {activeTab === 'Overview' && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                  <div className="text-sm text-white/50 mb-1">Status</div>
                  <div className="text-lg font-medium text-white">{previewModel.status}</div>
                </div>
                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                  <div className="text-sm text-white/50 mb-1">Duration</div>
                  <div className="text-lg font-medium text-white">{previewModel.durationText}</div>
                </div>
              </div>
              
              {previewModel.status === 'Failed' && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 text-sm">
                  <div className="flex items-center gap-2 font-medium mb-1">
                    <AlertTriangle className="w-4 h-4 text-red-400" /> Experiment Failed
                  </div>
                  The experiment halted unexpectedly. Check the Timeline or Logs for the exact failure point.
                </div>
              )}
            </div>
          )}

          {activeTab === 'Timeline' && (
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="relative border-l border-white/10 ml-2.5 pb-4 space-y-6">
                {previewModel.stages.map((stage) => {
                  const isHovered = hoveredStageId === stage.id;
                  const isFailed = stage.status === 'failed';
                  const isSkipped = stage.status === 'skipped';
                  const isActive = stage.status === 'active';

                  return (
                    <div 
                      key={stage.id} 
                      className="relative pl-6"
                      onMouseEnter={() => setHoveredStageId(stage.id)}
                      onMouseLeave={() => setHoveredStageId(null)}
                    >
                      <div className="absolute -left-[11px] top-0 bg-[#0F1117] py-1">
                        <StageIcon status={stage.status} />
                      </div>
                      
                      <div 
                        className={`
                          p-3 rounded-xl border transition-all cursor-pointer
                          ${isHovered ? 'border-white/20 bg-white/5' : 'border-transparent hover:border-white/10 hover:bg-white/[0.02]'}
                          ${isActive ? 'border-indigo-500/30 bg-indigo-500/5' : ''}
                          ${isFailed ? 'border-red-500/30 bg-red-500/5' : ''}
                        `}
                        onClick={() => handleStageClick(stage.id)}
                      >
                        <div className="flex justify-between items-center mb-1">
                          <h4 className={`text-sm font-medium ${isFailed ? 'text-red-400' : isSkipped ? 'text-white/40' : 'text-white/90'}`}>
                            {stage.name}
                          </h4>
                          <ChevronRight className={`w-4 h-4 ${isHovered ? 'text-white/50' : 'text-transparent'} transition-colors`} />
                        </div>
                        
                        {!isSkipped && (
                          <div className="flex items-center gap-3 text-xs text-white/50">
                            <span className="capitalize">{stage.status}</span>
                            {stage.durationMs !== undefined && (
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {Math.floor(stage.durationMs / 1000)}s
                              </span>
                            )}
                          </div>
                        )}
                        
                        {isFailed && (
                          <div className="mt-2 text-xs text-red-300/80 bg-red-500/10 p-2 rounded border border-red-500/20">
                            Execution halted at this stage. Remaining stages skipped.
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === 'Metrics' && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
              {Object.keys(previewModel.metrics).length === 0 ? (
                <div className="text-center py-12 text-white/40 text-sm">
                  <Activity className="w-8 h-8 mx-auto mb-3 opacity-50" />
                  No metrics computed yet.
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(previewModel.metrics).map(([key, value]) => (
                    <div key={key} className="p-4 rounded-xl bg-white/5 border border-white/10">
                      <div className="text-sm text-white/50 mb-1 capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}</div>
                      <div className="text-2xl font-medium text-white">{value}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'Configuration' && (
            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
              {Object.entries(previewModel.config).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10 text-sm">
                  <span className="text-white/50 capitalize">{key}</span>
                  <span className="text-white/90 font-mono">{String(value)}</span>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'Logs' && (
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300 bg-[#0A0C10] rounded-xl border border-white/10 font-mono text-xs overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2 border-b border-white/5 bg-white/5 text-white/40">
                <Terminal className="w-4 h-4" /> Live Execution Logs
              </div>
              <div className="p-4 space-y-2">
                {previewModel.logs.length === 0 ? (
                  <div className="text-white/30 text-center py-4">No logs available.</div>
                ) : (
                  previewModel.logs.map(log => {
                    const isRelated = hoveredStageId === log.stageId || selectedStageId === log.stageId;
                    return (
                      <div 
                        key={log.id} 
                        id={`log-stage-${log.stageId}`}
                        className={`
                          flex gap-3 py-1 px-2 rounded transition-colors
                          ${isRelated ? 'bg-indigo-500/20' : 'hover:bg-white/5'}
                        `}
                        onMouseEnter={() => setHoveredStageId(log.stageId)}
                        onMouseLeave={() => setHoveredStageId(null)}
                      >
                        <span className="text-white/30 shrink-0">
                          {new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                        <span className={`
                          shrink-0 uppercase w-10
                          ${log.level === 'error' ? 'text-red-400' : log.level === 'warn' ? 'text-yellow-400' : log.level === 'debug' ? 'text-white/40' : 'text-blue-400'}
                        `}>
                          {log.level}
                        </span>
                        <span className="text-white/70 break-all">{log.message}</span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
