import { AlertTriangle, RefreshCw } from 'lucide-react';
import type { useProviderCatalog } from '../../hooks/useProviderCatalog';

interface Props {
  catalog: ReturnType<typeof useProviderCatalog>;
}

export function AtlasProviderErrorState({ catalog }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
      <div className="h-12 w-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-4">
        <AlertTriangle className="w-6 h-6 text-red-400" />
      </div>
      
      <h3 className="text-lg font-medium text-white mb-2">
        Failed to load providers
      </h3>
      
      <p className="text-sm text-white/40 max-w-[280px] mb-6">
        {catalog.error?.message || "An unexpected error occurred while loading the provider registry."}
      </p>

      <button
        onClick={catalog.handleRetry}
        className="inline-flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-white transition-colors"
      >
        <RefreshCw className="w-4 h-4" />
        Retry loading
      </button>
    </div>
  );
}
