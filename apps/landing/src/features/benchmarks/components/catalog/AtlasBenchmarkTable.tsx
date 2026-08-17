import { useBenchmarkCatalog } from '../../hooks/useBenchmarkCatalog';

export function AtlasBenchmarkTable({ catalog }: { catalog: ReturnType<typeof useBenchmarkCatalog> }) {
  const { rows, selectedIds, handleSelect, handleSelectAll, sort, setSort, rawVisibleIds } = catalog;

  const allSelected = rawVisibleIds.length > 0 && rawVisibleIds.every((id: string) => selectedIds.includes(id));
  const someSelected = selectedIds.length > 0 && !allSelected;

  const SortIcon = ({ field }: { field: typeof sort.field }) => {
    if (sort.field !== field) return <span className="text-white/20 opacity-0 group-hover:opacity-100 ml-1 transition-opacity duration-[160ms]">↕</span>;
    return <span className="text-indigo-400 ml-1 transition-transform duration-[160ms] inline-block">{sort.direction === 'asc' ? '↑' : '↓'}</span>;
  };

  const handleSort = (field: typeof sort.field) => {
    if (sort.field === field) {
      setSort({ field, direction: sort.direction === 'asc' ? 'desc' : 'asc' });
    } else {
      setSort({ field, direction: 'desc' });
    }
  };

  return (
    <div className="w-full border border-white/10 rounded-2xl overflow-hidden bg-white/5">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-white/70">
          <thead className="bg-black/40 border-b border-white/10 text-white/50 text-xs uppercase tracking-wider">
            <tr>
              <th className="p-4 w-12">
                <input 
                  type="checkbox"
                  className="w-4 h-4 rounded border-white/20 bg-black/50 text-indigo-500 focus:ring-indigo-500 cursor-pointer"
                  checked={allSelected}
                  ref={input => { if (input) input.indeterminate = someSelected; }}
                  onChange={() => handleSelectAll(rawVisibleIds)}
                />
              </th>
              <th className="p-4 cursor-pointer group hover:text-white transition-colors" onClick={() => handleSort('name')}>
                Benchmark <SortIcon field="name" />
              </th>
              <th className="p-4 cursor-pointer group hover:text-white transition-colors" onClick={() => handleSort('verificationScore')}>
                Score <SortIcon field="verificationScore" />
              </th>
              <th className="p-4 cursor-pointer group hover:text-white transition-colors" onClick={() => handleSort('tasksCount')}>
                Tasks <SortIcon field="tasksCount" />
              </th>
              <th className="p-4 cursor-pointer group hover:text-white transition-colors" onClick={() => handleSort('updatedAt')}>
                Updated <SortIcon field="updatedAt" />
              </th>
              <th className="p-4">Category</th>
              <th className="p-4">Difficulty</th>
              <th className="p-4">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {rows.map((row: any) => {
              const isSelected = selectedIds.includes(row.id);
              const handleClick = (e: React.MouseEvent) => {
                if (e.detail === 2) {
                  catalog.handleOpenPreview(row.id);
                } else if (e.shiftKey) {
                  catalog.handleRangeSelect(row.id, rawVisibleIds);
                } else {
                  catalog.handleSelect(row.id, e.ctrlKey || e.metaKey);
                }
              };

              return (
                <tr 
                  key={row.id} 
                  className={`group cursor-pointer transition-all duration-[160ms] select-none ${isSelected ? 'bg-indigo-500/10' : 'hover:bg-white/[0.03]'}`}
                  onClick={handleClick}
                >
                  <td className={`p-4 border-l-2 transition-colors duration-[160ms] ${isSelected ? 'border-indigo-500' : 'border-transparent group-hover:border-indigo-500/30'}`} onClick={(e) => e.stopPropagation()}>
                    <input 
                      type="checkbox"
                      className="w-4 h-4 rounded border-white/20 bg-black/50 text-indigo-500 focus:ring-indigo-500 cursor-pointer"
                      checked={isSelected}
                      onChange={() => handleSelect(row.id, true)}
                    />
                  </td>
                  <td className="p-4">
                    <span className="text-white font-medium">{row.name}</span>
                  </td>
                  <td className="p-4 whitespace-nowrap">{row.verificationScore}</td>
                  <td className="p-4 whitespace-nowrap">{row.tasksCountFormatted}</td>
                  <td className="p-4 whitespace-nowrap">{row.updatedAt}</td>
                  <td className="p-4 capitalize">{row.category}</td>
                  <td className="p-4 capitalize">{row.difficulty}</td>
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded-md text-xs font-medium ${row.status === 'Ready' || row.status === 'Running' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
                      {row.status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
