export function AtlasProviderSkeleton({ viewMode }: { viewMode: 'grid' | 'table' }) {
  if (viewMode === 'table') {
    return (
      <div className="w-full">
        {/* Header Skeleton */}
        <div className="flex items-center px-4 py-3 border-b border-white/5 bg-white/[0.02]">
          <div className="w-8 h-4 rounded bg-white/5 animate-pulse" />
          <div className="w-48 h-4 ml-4 rounded bg-white/5 animate-pulse" />
          <div className="w-32 h-4 ml-auto rounded bg-white/5 animate-pulse" />
          <div className="w-24 h-4 ml-8 rounded bg-white/5 animate-pulse" />
        </div>
        
        {/* Row Skeletons */}
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center px-4 py-4 border-b border-white/5">
            <div className="w-4 h-4 rounded bg-white/5 animate-pulse" />
            <div className="flex items-center gap-3 ml-4">
              <div className="w-8 h-8 rounded bg-white/5 animate-pulse" />
              <div className="w-32 h-4 rounded bg-white/5 animate-pulse" />
            </div>
            <div className="w-24 h-4 ml-auto rounded bg-white/5 animate-pulse" />
            <div className="w-16 h-4 ml-8 rounded bg-white/5 animate-pulse" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="p-4 rounded-xl border border-white/5 bg-white/[0.02] flex flex-col gap-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-white/5 animate-pulse" />
              <div className="space-y-2">
                <div className="w-24 h-4 rounded bg-white/5 animate-pulse" />
                <div className="w-16 h-3 rounded bg-white/5 animate-pulse" />
              </div>
            </div>
          </div>
          
          <div className="space-y-2 mt-2">
            <div className="w-full h-3 rounded bg-white/5 animate-pulse" />
            <div className="w-4/5 h-3 rounded bg-white/5 animate-pulse" />
          </div>

          <div className="flex gap-2 mt-auto pt-4 border-t border-white/5">
            <div className="w-16 h-6 rounded-full bg-white/5 animate-pulse" />
            <div className="w-16 h-6 rounded-full bg-white/5 animate-pulse" />
          </div>
        </div>
      ))}
    </div>
  );
}
