import { useDatasetCatalog } from '../../hooks/useDatasetCatalog';

export function AtlasPagination({ catalog }: { catalog: ReturnType<typeof useDatasetCatalog> }) {
  const { pagination, setPagination } = catalog;
  const { page, pageSize, total } = pagination;
  
  const totalPages = Math.ceil(total / pageSize);
  
  if (total === 0) return null;

  return (
    <div className="flex items-center justify-between border-t border-white/10 pt-4 mt-2">
      <div className="flex items-center gap-2 text-sm text-white/50">
        <span>Showing</span>
        <select 
          className="bg-black/50 border border-white/10 rounded-md px-2 py-1 text-white focus:outline-none focus:border-indigo-500"
          value={pageSize}
          onChange={(e) => setPagination({ ...pagination, page: 1, pageSize: Number(e.target.value) })}
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
        <span>of {total} datasets</span>
      </div>

      <div className="flex items-center gap-1">
        <button 
          disabled={page === 1}
          onClick={() => setPagination({ ...pagination, page: page - 1 })}
          className="px-3 py-1.5 rounded-lg border border-white/10 text-white/60 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:hover:bg-transparent transition-colors text-sm"
        >
          Previous
        </button>
        <div className="px-4 py-1.5 text-sm text-white/80">
          Page {page} of {totalPages || 1}
        </div>
        <button 
          disabled={page >= totalPages}
          onClick={() => setPagination({ ...pagination, page: page + 1 })}
          className="px-3 py-1.5 rounded-lg border border-white/10 text-white/60 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:hover:bg-transparent transition-colors text-sm"
        >
          Next
        </button>
      </div>
    </div>
  );
}
