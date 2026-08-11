export function AtlasBenchmarkErrorState({ catalog }: { catalog: any }) {
  return (
    <div className="w-full py-20 flex flex-col items-center justify-center text-red-400 border border-red-500/20 rounded-2xl bg-red-500/5">
      <h3 className="text-lg mb-2">Failed to load benchmarks</h3>
      <p className="text-sm opacity-80 mb-6">{catalog.error?.message || 'An unknown error occurred.'}</p>
      <button onClick={catalog.retry} className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 rounded-xl transition-colors text-white">Retry</button>
    </div>
  );
}
