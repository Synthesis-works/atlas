import React, { useState } from 'react';
import { Network, Cpu, Globe, Server, Activity, ShieldCheck, Zap, Layers } from 'lucide-react';
import { useModelsStore } from '../store/modelsStore';

interface PodReplica {
  id: string;
  name: string;
  traffic: string;
  status: 'healthy' | 'degraded';
  gpuMemory: string;
}

const POD_REPLICAS: PodReplica[] = [
  { id: 'pod-01', name: 'vllm-llama3-70b-pod-01', traffic: '140 req/s', status: 'healthy', gpuMemory: '18.4 GB / 80 GB' },
  { id: 'pod-02', name: 'vllm-llama3-70b-pod-02', traffic: '140 req/s', status: 'healthy', gpuMemory: '18.2 GB / 80 GB' },
  { id: 'pod-03', name: 'vllm-llama3-70b-pod-03', traffic: '140 req/s', status: 'degraded', gpuMemory: '78.9 GB / 80 GB' },
];

export const FleetTopology: React.FC = () => {
  const { openDrawer, models } = useModelsStore();
  const [activePodId, setActivePodId] = useState('pod-03');

  const selectedPod = POD_REPLICAS.find((p) => p.id === activePodId) || POD_REPLICAS[0];

  const handleInspectModel = () => {
    const matched = models.find((m) => m.name.toLowerCase().includes('llama'));
    if (matched) openDrawer(matched, 'metrics');
  };

  return (
    <div className="liquid-glass-card rounded-2xl p-5 border border-white/10 space-y-4">
      {/* Topology Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-3">
        <div>
          <div className="flex items-center gap-2 font-mono text-xs text-accent uppercase tracking-wider mb-0.5">
            <Network className="w-4 h-4 text-emerald-400 animate-pulse" />
            <span>Signature Infrastructure Topology Graph</span>
          </div>
          <h3 className="text-sm font-semibold text-white tracking-tight">
            Cluster Node Hierarchy & Pod Replica Distribution
          </h3>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="flex items-center gap-1.5 text-emerald-400 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> 3 Active Pod Replicas
          </span>
          <span className="text-white/20">•</span>
          <span className="text-white/40">420 req/s Total Traffic</span>
        </div>
      </div>

      {/* Visual Infrastructure Tree Graph Surface */}
      <div className="p-5 rounded-xl border border-white/5 bg-white/[0.01] overflow-x-auto scrollbar-thin scrollbar-thumb-white/10">
        <div className="min-w-[720px] flex flex-col items-center gap-4 relative">
          {/* Level 1: Provider & Region Hubs */}
          <div className="flex items-center justify-center gap-12">
            <div className="px-4 py-2 rounded-xl border border-white/15 bg-white/[0.03] flex items-center gap-2 font-mono text-xs text-white shadow-md">
              <Globe className="w-4 h-4 text-accent shrink-0" />
              <span>Provider: OpenAI Cloud</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
            </div>

            <div className="w-16 h-px bg-gradient-to-r from-white/20 to-emerald-400/50" />

            <div className="px-4 py-2 rounded-xl border border-white/15 bg-white/[0.03] flex items-center gap-2 font-mono text-xs text-white shadow-md">
              <Server className="w-4 h-4 text-blue-400 shrink-0" />
              <span>AWS Cluster: us-east-1</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
            </div>
          </div>

          {/* SVG Connecting Tree Stem */}
          <svg className="w-full h-8 overflow-visible" preserveAspectRatio="none" viewBox="0 0 600 32">
            <path d="M 300 0 L 300 16 M 120 32 L 120 16 L 480 16 L 480 32 M 300 16 L 300 32" stroke="rgba(255,255,255,0.15)" strokeWidth="1.5" fill="none" strokeDasharray="3 3" />
          </svg>

          {/* Level 2: GPU Pool Node */}
          <div className="px-5 py-2.5 rounded-xl border border-purple-500/30 bg-purple-950/20 flex items-center gap-3 font-mono text-xs text-purple-200 shadow-[0_0_20px_rgba(168,85,247,0.15)]">
            <Cpu className="w-4 h-4 text-purple-400 shrink-0" />
            <span className="font-semibold">GPU Resource Pool: NVIDIA A100 80GB (32 GPUs)</span>
            <span className="px-2 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30 font-bold">78% Saturation</span>
          </div>

          {/* SVG Branching Lines to Pod Replicas */}
          <svg className="w-full h-8 overflow-visible" preserveAspectRatio="none" viewBox="0 0 600 32">
            <path d="M 300 0 L 300 16 M 100 32 L 100 16 L 500 16 L 500 32 M 300 16 L 300 32" stroke="rgba(99,102,241,0.4)" strokeWidth="1.5" fill="none" />
          </svg>

          {/* Level 3: Pod Replicas Row */}
          <div className="grid grid-cols-3 gap-4 w-full">
            {POD_REPLICAS.map((pod) => {
              const isSelected = pod.id === activePodId;
              const isDegraded = pod.status === 'degraded';

              return (
                <button
                  key={pod.id}
                  onClick={() => { setActivePodId(pod.id); handleInspectModel(); }}
                  className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                    isSelected ? 'ring-2 ring-accent scale-[1.02]' : ''
                  } ${
                    isDegraded
                      ? 'border-amber-500/40 bg-amber-950/20 text-amber-300 shadow-[0_0_15px_rgba(245,158,11,0.15)]'
                      : 'border-emerald-500/30 bg-emerald-950/20 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.15)]'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-white/50 font-bold flex items-center gap-1">
                      <Layers className="w-3 h-3 text-accent" /> Pod Replica
                    </span>
                    <span className={`w-2 h-2 rounded-full ring-2 ${isDegraded ? 'bg-amber-400 ring-amber-400/20 animate-pulse' : 'bg-emerald-400 ring-emerald-400/20'}`} />
                  </div>
                  <div className="text-xs font-mono font-bold text-white truncate">{pod.name}</div>
                  <div className="flex items-center justify-between gap-2 mt-2 pt-2 border-t border-white/10 text-[10px] font-mono">
                    <span className="text-white/60 font-semibold">{pod.traffic}</span>
                    <span className="text-white/40">{pod.gpuMemory}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Selected Pod Telemetry Detail Bar */}
      <div className="p-3 rounded-xl border border-white/10 bg-white/[0.02] flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-1.5 rounded-lg bg-white/5 border border-white/10 text-accent">
            <Zap className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="min-w-0">
            <span className="text-white/40">Pod Focus: </span>
            <span className="text-white font-semibold">{selectedPod.name}</span>
            <span className="text-white/30 truncate"> ({selectedPod.gpuMemory})</span>
          </div>
        </div>

        <div className="flex items-center gap-4 text-white/60 shrink-0">
          <span className="flex items-center gap-1 text-emerald-400">
            <Activity className="w-3.5 h-3.5" /> Traffic: {selectedPod.traffic}
          </span>
          <span className="flex items-center gap-1 text-accent">
            <ShieldCheck className="w-3.5 h-3.5" /> Readiness Probe: Passed
          </span>
        </div>
      </div>
    </div>
  );
};
