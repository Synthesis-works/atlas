import { useDatasetCatalog } from '../../hooks/useDatasetCatalog';

export function AtlasDatasetSkeleton({ catalog }: { catalog: ReturnType<typeof useDatasetCatalog> }) {
  if (catalog.viewMode === 'table') {
    return (
      <div className="w-full border border-white/10 rounded-2xl overflow-hidden bg-white/5">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-black/40 border-b border-white/10">
              <tr>
                <th className="p-4 w-12"><div className="w-4 h-4 rounded bg-white/10 animate-pulse" /></th>
                <th className="p-4"><div className="w-24 h-4 rounded bg-white/10 animate-pulse" /></th>
                <th className="p-4"><div className="w-20 h-4 rounded bg-white/10 animate-pulse" /></th>
                <th className="p-4"><div className="w-16 h-4 rounded bg-white/10 animate-pulse" /></th>
                <th className="p-4"><div className="w-16 h-4 rounded bg-white/10 animate-pulse" /></th>
                <th className="p-4"><div className="w-12 h-4 rounded bg-white/10 animate-pulse" /></th>
                <th className="p-4"><div className="w-20 h-4 rounded bg-white/10 animate-pulse" /></th>
                <th className="p-4"><div className="w-16 h-4 rounded bg-white/10 animate-pulse" /></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  <td className="p-4"><div className="w-4 h-4 rounded bg-white/5 animate-pulse" /></td>
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded bg-white/5 animate-pulse" />
                      <div className="flex flex-col gap-2">
                        <div className="w-32 h-4 rounded bg-white/5 animate-pulse" />
                        <div className="w-24 h-3 rounded bg-white/5 animate-pulse" />
                      </div>
                    </div>
                  </td>
                  <td className="p-4"><div className="w-16 h-4 rounded bg-white/5 animate-pulse" /></td>
                  <td className="p-4"><div className="w-12 h-4 rounded bg-white/5 animate-pulse" /></td>
                  <td className="p-4"><div className="w-12 h-4 rounded bg-white/5 animate-pulse" /></td>
                  <td className="p-4"><div className="w-16 h-4 rounded bg-white/5 animate-pulse" /></td>
                  <td className="p-4"><div className="w-20 h-4 rounded bg-white/5 animate-pulse" /></td>
                  <td className="p-4"><div className="w-16 h-4 rounded bg-white/5 animate-pulse" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <ul className="w-full grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] items-start gap-6">
      {Array.from({ length: 6 }).map((_, i) => (
        <li key={i} className="flex flex-col bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
          <div className="h-48 w-full bg-white/10 animate-pulse" />
          <div className="flex flex-col p-5 gap-3">
            <div className="w-3/4 h-5 rounded bg-white/10 animate-pulse" />
            <div className="flex justify-between mt-2">
              <div className="w-1/3 h-4 rounded bg-white/5 animate-pulse" />
              <div className="w-1/4 h-4 rounded bg-white/5 animate-pulse" />
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
