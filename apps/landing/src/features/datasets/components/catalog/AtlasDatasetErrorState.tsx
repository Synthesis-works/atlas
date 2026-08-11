import { AlertTriangle, ServerCrash } from 'lucide-react';
import { useDatasetCatalog } from '../../hooks/useDatasetCatalog';

export function AtlasDatasetErrorState({ catalog }: { catalog: ReturnType<typeof useDatasetCatalog> }) {
  const { error, retry } = catalog;
  if (!error) return null;

  const Icon = error.recoverable ? AlertTriangle : ServerCrash;

  return (
    <div className="w-full h-64 flex flex-col items-center justify-center border border-dashed border-red-500/20 rounded-2xl bg-red-500/[0.02]">
      <div className="flex flex-col items-center max-w-md text-center">
        <div className="h-12 w-12 rounded-xl bg-red-500/10 flex items-center justify-center mb-4 text-red-400">
          <Icon className="w-6 h-6" />
        </div>
        
        <h3 className="text-white font-medium text-lg mb-1">
          {error.recoverable ? 'Could not load datasets' : 'System Error'}
        </h3>
        
        <p className="text-white/50 text-sm mb-6">
          {error.message || 'An unexpected error occurred while communicating with the server.'}
          {!error.recoverable && (
            <span className="block mt-2 text-white/30 text-xs">
              Please contact your administrator or check the documentation for support.
            </span>
          )}
        </p>
        
        {error.recoverable && retry && (
          <button 
            onClick={retry}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-sm font-medium rounded-lg transition-colors border border-white/5"
          >
            Retry Request
          </button>
        )}
      </div>
    </div>
  );
}
