import { useModelsStore } from '../store/modelsStore';

export function VersionTimeline() {
  const { models } = useModelsStore();

  // Build family groups
  const families: Record<string, typeof models> = {};
  models.forEach(m => {
    if (!families[m.family]) families[m.family] = [];
    families[m.family].push(m);
  });

  // Pick top 4 families by model count
  const top4 = Object.entries(families)
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 4);

  return (
    <div className="liquid-glass-card rounded-2xl overflow-hidden h-full flex flex-col">
      <div className="px-4 py-3 border-b border-white/[0.05] shrink-0">
        <span className="text-xs text-white/40 font-medium uppercase tracking-wider">Version Timeline</span>
      </div>
      <div className="p-4 space-y-6">
        {top4.map(([family, fmodels]) => {
          const sorted = [...fmodels].sort((a, b) => new Date(a.releaseDate).getTime() - new Date(b.releaseDate).getTime());
          return (
            <div key={family}>
              <p className="text-xs text-white/25 mb-3 uppercase tracking-wider">{family}</p>
              <div className="flex items-center gap-0 flex-wrap">
                {sorted.map((m, i) => (
                  <div key={m.id} className="flex items-center gap-0">
                    <div className="flex flex-col items-center">
                      <div className={`w-2.5 h-2.5 rounded-full border-2 ${
                        m.status === 'active'
                          ? 'bg-accent border-accent/50'
                          : 'bg-white/10 border-white/20'
                      }`} />
                      <p className="text-[10px] text-white/40 mt-1 whitespace-nowrap max-w-[72px] text-center truncate">
                        {m.name}
                      </p>
                      <p className="text-[9px] text-white/20 whitespace-nowrap">
                        {m.releaseDate.slice(0, 7)}
                      </p>
                    </div>
                    {i < sorted.length - 1 && (
                      <div className="w-8 h-px bg-white/[0.08] mx-1 mb-5" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
