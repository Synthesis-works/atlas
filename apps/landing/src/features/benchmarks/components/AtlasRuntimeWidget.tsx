import React, { useEffect, useState } from 'react';
import { Cpu, Wifi, WifiOff } from 'lucide-react';
import { apiClient } from '@/core/api/client';

export const AtlasRuntimeWidget: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState<{
    connected: boolean;
    version?: string;
    loading: boolean;
  }>({
    connected: false,
    version: undefined,
    loading: true,
  });

  useEffect(() => {
    let mounted = true;

    async function checkHealth() {
      try {
        const res = await apiClient.get<any>('/api/v1/health');
        const data = res?.data || res;
        if (mounted) {
          if (data && (data.status === 'ok' || data.status === 'healthy')) {
            setHealthStatus({
              connected: true,
              version: data.version,
              loading: false,
            });
          } else {
            setHealthStatus({ connected: false, loading: false });
          }
        }
      } catch (_) {
        if (mounted) {
          setHealthStatus({ connected: false, loading: false });
        }
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="fixed bottom-6 right-6 z-40 p-3.5 rounded-2xl border border-white/10 bg-neutral-950/90 backdrop-blur-xl shadow-2xl space-y-2 text-xs font-mono select-none">
      <div className="flex items-center justify-between gap-4 border-b border-white/5 pb-2">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-accent" />
          <span className="font-bold text-white tracking-wider">Atlas Runtime</span>
        </div>
        {healthStatus.connected ? (
          <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Wifi className="w-3 h-3" />
            Connected
          </span>
        ) : (
          <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
            <WifiOff className="w-3 h-3" />
            Offline
          </span>
        )}
      </div>

      {healthStatus.connected ? (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-white/50">
          <div className="flex items-center justify-between gap-2">
            <span>API:</span>
            <span className="text-emerald-400 font-medium">Online</span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span>Version:</span>
            <span className="text-white/80 font-medium">v{healthStatus.version || '0.9.0'}</span>
          </div>
        </div>
      ) : (
        <div className="text-[11px] text-white/40 italic py-0.5">
          Runtime telemetry unavailable
        </div>
      )}
    </div>
  );
};

export default AtlasRuntimeWidget;
