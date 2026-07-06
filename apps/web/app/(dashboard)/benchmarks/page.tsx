export default function BenchmarksPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Benchmarks</h1>
          <p className="text-muted-foreground mt-1">Discover, view, and understand available evaluation benchmarks.</p>
        </div>
        <button className="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-md font-medium text-sm transition-colors">
          Create Benchmark
        </button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="p-6 rounded-xl border bg-card text-card-foreground shadow-sm">
            <div className="w-10 h-10 rounded bg-muted animate-pulse mb-4" />
            <div className="h-4 w-1/2 bg-muted animate-pulse rounded mb-2" />
            <div className="h-3 w-3/4 bg-muted animate-pulse rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}
