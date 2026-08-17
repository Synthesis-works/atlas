import { useState, useEffect } from 'react';
import { useDatasetCatalog } from '../../hooks/useDatasetCatalog';


interface AtlasDatasetSearchProps {
  catalog: ReturnType<typeof useDatasetCatalog>;
  inputRef?: React.RefObject<HTMLInputElement | null>;
}

export function AtlasDatasetSearch({ catalog, inputRef }: AtlasDatasetSearchProps) {
  const [localQuery, setLocalQuery] = useState(catalog.filters.searchQuery);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (localQuery !== catalog.filters.searchQuery) {
        catalog.handleSearch(localQuery);
      }
    }, 300); // 300ms debounce

    return () => clearTimeout(timer);
  }, [localQuery, catalog]);

  // Sync back if external change happens
  useEffect(() => {
    setLocalQuery(catalog.filters.searchQuery);
  }, [catalog.filters.searchQuery]);

  return (
    <div className="relative flex-1 w-full lg:max-w-md">
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <svg className="h-4 w-4 text-white/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
      <input
        ref={inputRef}
        type="text"
        className="block w-full pl-10 pr-3 py-2 border border-white/10 rounded-lg leading-5 bg-black/50 text-white/40 placeholder-white/20 focus:outline-none sm:text-sm cursor-not-allowed"
        placeholder="Search is temporarily unavailable (Awaiting Backend Support)"
        value=""
        disabled
        title="Search is temporarily unavailable because the backend does not currently support it."
        onChange={(e) => setLocalQuery(e.target.value)}
      />
      {/* Search is disabled, hide the clear button */}
    </div>
  );
}
