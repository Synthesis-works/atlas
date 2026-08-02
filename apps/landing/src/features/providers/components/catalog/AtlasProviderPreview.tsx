import { useEffect, useRef } from 'react';
import { X, ExternalLink, Shield, Server, Activity, Globe } from 'lucide-react';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';
import type { useProviderCatalog } from '../../hooks/useProviderCatalog';

interface Props {
  catalog: ReturnType<typeof useProviderCatalog>;
}

export function AtlasProviderPreview({ catalog }: Props) {
  const { previewModel, handleClosePreview } = catalog;
  
  const activeTab = useWorkspaceInteractionStore(s => s.workspaces['providers']?.view.activePreviewTab || 'Overview');
  const setActiveTab = useWorkspaceInteractionStore(s => s.setActivePreviewTab);
  const setScrollPosition = useWorkspaceInteractionStore(s => s.setScrollPosition);
  const savedScroll = useWorkspaceInteractionStore(s => s.workspaces['providers']?.navigation.scrollPosition || 0);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Restore scroll position
  useEffect(() => {
    if (scrollRef.current && savedScroll > 0) {
      scrollRef.current.scrollTop = savedScroll;
    }
  }, [previewModel?.id]);

  if (!previewModel) return null;

  const StatusIcon = ({ status }: { status: string }) => {
    switch (status) {
      case 'operational': return <div className="w-2 h-2 rounded-full bg-emerald-400" />;
      case 'degraded': return <div className="w-2 h-2 rounded-full bg-yellow-400" />;
      case 'outage': return <div className="w-2 h-2 rounded-full bg-red-400" />;
      default: return <div className="w-2 h-2 rounded-full bg-slate-400" />;
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
            <span className="capitalize">{previewModel.tier} Tier</span>
            <span>•</span>
            <span>Updated {new Date(previewModel.updatedAt).toLocaleDateString()}</span>
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
      <div className="flex px-4 border-b border-white/5 shrink-0">
        {['Overview', 'Infrastructure', 'Compliance'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab('providers', tab)}
            className={`
              px-4 py-3 text-sm font-medium border-b-2 transition-colors
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
          setScrollPosition('providers', (e.target as HTMLDivElement).scrollTop);
        }}
      >
        <div className="p-6 space-y-8">
          {activeTab === 'Overview' && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div>
                <h3 className="text-sm font-medium text-white/70 mb-2">About</h3>
                <p className="text-sm text-white/50 leading-relaxed">
                  {previewModel.description}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                  <div className="flex items-center gap-2 text-sm text-white/50 mb-2">
                    <Server className="w-4 h-4" /> Available Models
                  </div>
                  <div className="text-2xl font-medium">{previewModel.modelsCount}</div>
                </div>
                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                  <div className="flex items-center gap-2 text-sm text-white/50 mb-2">
                    <Activity className="w-4 h-4" /> Avg Latency
                  </div>
                  <div className="text-2xl font-medium">{previewModel.averageLatencyMs}ms</div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-medium text-white/70 mb-3">Supported Modalities</h3>
                <div className="flex flex-wrap gap-2">
                  {previewModel.supportedModalities.map(mod => (
                    <span key={mod} className="text-xs px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 capitalize">
                      {mod}
                    </span>
                  ))}
                </div>
              </div>

              <div className="pt-4">
                <a 
                  href={previewModel.apiEndpoint}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center">
                      <Globe className="w-4 h-4 text-white/60" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-white">API Endpoint</div>
                      <div className="text-xs text-white/40">{previewModel.apiEndpoint}</div>
                    </div>
                  </div>
                  <ExternalLink className="w-4 h-4 text-white/40 group-hover:text-white transition-colors" />
                </a>
              </div>
            </div>
          )}

          {activeTab === 'Infrastructure' && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <div className="flex items-center gap-2 text-sm text-white/50 mb-2">
                  Global Uptime SLA
                </div>
                <div className="text-3xl font-medium text-emerald-400">
                  {previewModel.uptimePercentage}%
                </div>
                <div className="mt-2 text-xs text-white/40">Based on 90-day historical data</div>
              </div>

              <div>
                <h3 className="text-sm font-medium text-white/70 mb-3">Available Regions</h3>
                <div className="flex flex-wrap gap-2">
                  {previewModel.regions.map(r => (
                    <span key={r} className="text-xs px-2.5 py-1 rounded bg-white/5 text-white/60 border border-white/10 font-mono">
                      {r}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'Compliance' && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div>
                <h3 className="text-sm font-medium text-white/70 mb-3 flex items-center gap-2">
                  <Shield className="w-4 h-4" /> Certifications
                </h3>
                <div className="space-y-2">
                  {previewModel.compliance.map(cert => (
                    <div key={cert} className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10">
                      <span className="text-sm font-medium text-white/80">{cert}</span>
                      <Shield className="w-4 h-4 text-emerald-400" />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
