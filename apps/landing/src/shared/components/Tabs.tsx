
import { cn } from '@/lib/utils';

export interface TabOption<T extends string = string> {
  id: T;
  label: string;
  badge?: number | string;
}

interface TabsProps<T extends string> {
  options: TabOption<T>[];
  activeId: T;
  onChange: (id: T) => void;
  className?: string;
}

export function Tabs<T extends string>({ options, activeId, onChange, className }: TabsProps<T>) {
  return (
    <div className={cn('flex flex-wrap items-center gap-1.5 p-1 rounded-xl bg-white/[0.03] border border-white/5', className)}>
      {options.map((tab) => {
        const isActive = tab.id === activeId;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all select-none',
              isActive
                ? 'bg-accent/20 text-accent border border-accent/30 shadow-sm'
                : 'text-white/40 hover:text-white hover:bg-white/5'
            )}
          >
            {tab.label}
            {tab.badge !== undefined && (
              <span
                className={cn(
                  'px-1.5 py-0.2 rounded-full text-[10px]',
                  isActive ? 'bg-accent/30 text-white' : 'bg-white/10 text-white/40'
                )}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default Tabs;
