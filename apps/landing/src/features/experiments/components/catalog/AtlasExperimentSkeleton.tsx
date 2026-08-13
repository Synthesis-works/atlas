export function AtlasExperimentSkeleton() {
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
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex items-center px-4 py-4 border-b border-white/5">
          <div className="w-4 h-4 rounded bg-white/5 animate-pulse" />
          <div className="flex items-center gap-3 ml-4">
            <div className="w-48 h-4 rounded bg-white/5 animate-pulse" />
          </div>
          
          <div className="ml-auto w-32 h-4 rounded bg-white/5 animate-pulse" />
          <div className="w-48 h-4 ml-8 rounded bg-white/5 animate-pulse" />
        </div>
      ))}
    </div>
  );
}
