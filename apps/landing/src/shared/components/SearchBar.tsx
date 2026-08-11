import React from 'react';
import { Search, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  hints?: string[];
  onSelectHint?: (hint: string) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChange,
  placeholder = 'Search benchmarks, tags, status...',
  className,
  hints,
  onSelectHint,
}) => {
  return (
    <div className={cn('relative flex-1', className)}>
      <div className="relative flex items-center">
        <Search className="absolute left-3.5 w-4 h-4 text-white/30 pointer-events-none" />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full bg-white/[0.03] border border-white/10 rounded-xl pl-10 pr-10 py-2 text-xs text-white placeholder-white/30 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/50 transition-all font-mono"
        />
        {value && (
          <button
            onClick={() => onChange('')}
            className="absolute right-3 text-white/30 hover:text-white transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {hints && hints.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          <span className="text-[10px] text-white/20 font-mono self-center">Quick Filters:</span>
          {hints.map((hint) => (
            <button
              key={hint}
              onClick={() => onSelectHint?.(hint)}
              className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-white/40 hover:text-accent hover:bg-accent/10 border border-white/5 transition-colors"
            >
              {hint}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchBar;
