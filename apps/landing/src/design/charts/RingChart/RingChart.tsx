import React, { createContext, useContext } from 'react';
import { defaultRingColors } from '@/components/charts/ring-context';
import { RingChart } from '@/components/charts/ring-chart';
import { Ring } from '@/components/charts/ring';
import { RingCenter } from '@/components/charts/ring-center';

export { RingChart, Ring, RingCenter };

export interface RingItem {
  label: string;
  value: number;
  maxValue?: number;
  color?: string;
  percentage?: number;
}

export type { RingData } from '@/components/charts/ring-context';

/* ----------------------------------------------------------------------- */
/*  Legend context + primitives                                              */
/* ----------------------------------------------------------------------- */

interface LegendCtxValue {
  item:      RingItem;
  index:     number;
  isHovered: boolean;
  total:     number;
  prefix?:   string;
}

const LegendCtx = createContext<LegendCtxValue | null>(null);

function useLegendItem(): LegendCtxValue {
  const v = useContext(LegendCtx);
  if (!v) throw new Error('Legend sub-components must be inside <Legend>');
  return v;
}

/* Full legend list */
export const Legend: React.FC<{
  items:         RingItem[];
  hoveredIndex:  number | null;
  onHoverChange: (idx: number | null) => void;
  prefix?:       string;
  children:      React.ReactNode;
}> = ({ items, hoveredIndex, onHoverChange, prefix, children }) => {
  const total = items.reduce((s, d) => s + d.value, 0) || 1;
  return (
    <div className="w-full space-y-1.5 mt-3 font-mono text-xs">
      {items.map((item, index) => {
        const isHovered = hoveredIndex === index;
        return (
          <LegendCtx.Provider
            key={item.label}
            value={{ item, index, isHovered, total, prefix }}
          >
            <div
              onMouseEnter={() => onHoverChange(index)}
              onMouseLeave={() => onHoverChange(null)}
              className="cursor-pointer select-none transition-opacity duration-150"
              style={{ opacity: hoveredIndex !== null && !isHovered ? 0.35 : 1 }}
            >
              {children}
            </div>
          </LegendCtx.Provider>
        );
      })}
    </div>
  );
};

/* Dark-themed legend row — works on the atlas dark surface */
export const LegendItemComponent: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.07] hover:bg-white/[0.07] transition-colors duration-150">
    {children}
  </div>
);

export const LegendMarker: React.FC = () => {
  const { item, index } = useLegendItem();
  const color = item.color || defaultRingColors[index % defaultRingColors.length];
  return (
    <span
      className="w-2.5 h-2.5 rounded-sm shrink-0"
      style={{ backgroundColor: color }}
    />
  );
};

export const LegendLabel: React.FC = () => {
  const { item } = useLegendItem();
  return (
    <span className="text-white/70 font-medium truncate flex-1 text-xs">
      {item.label}
    </span>
  );
};

export const LegendValue: React.FC<{ showPercentage?: boolean }> = ({ showPercentage = false }) => {
  const { item, total, prefix } = useLegendItem();
  const pct = Math.round((item.value / total) * 100);
  return (
    <span className="text-white/90 font-bold font-mono shrink-0 text-xs tabular-nums">
      {prefix ?? ''}{item.value.toLocaleString()}
      {showPercentage && (
        <span className="text-white/35 text-[10px] ml-1 font-medium">({pct}%)</span>
      )}
    </span>
  );
};

export const LegendProgress: React.FC = () => {
  const { item, index, total } = useLegendItem();
  const pct   = (item.value / total) * 100;
  const color = item.color || defaultRingColors[index % defaultRingColors.length];
  return (
    <div className="w-14 h-1.5 rounded-full bg-white/[0.08] overflow-hidden shrink-0">
      <div
        className="h-full rounded-full transition-all duration-300"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
};

/* ----------------------------------------------------------------------- */
/*  RingCard — dark-themed, exact Bklit composition wrapper               */
/* ----------------------------------------------------------------------- */

export const RingCard: React.FC<{
  title:         string;
  subtitle?:     string;
  badge?:        string;
  data:          RingItem[];
  hoveredIndex:  number | null;
  onHoverChange: (idx: number | null) => void;
  prefix?:       string;
  size?:         number;
}> = ({ title, subtitle, badge, data, hoveredIndex, onHoverChange, prefix, size = 180 }) => {
  const maxVal = Math.max(...data.map((d) => d.value), 1);

  const formattedData = data.map((item, idx) => ({
    label:    item.label,
    value:    item.value,
    maxValue: item.maxValue ?? maxVal,
    color:    item.color || defaultRingColors[idx % defaultRingColors.length],
  }));

  return (
    <div className="flex flex-col items-center w-full bg-[#0c0c0e] border border-white/[0.08] rounded-2xl p-5 shadow-xl">
      {/* Header */}
      <div className="w-full flex items-start justify-between gap-2 mb-4">
        <div>
          <h4 className="text-sm font-semibold text-white tracking-tight">{title}</h4>
          {subtitle && (
            <p className="text-xs text-white/35 mt-0.5">{subtitle}</p>
          )}
        </div>
        {badge && (
          <span className="shrink-0 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium text-accent bg-accent/10 border border-accent/20">
            {badge}
          </span>
        )}
      </div>

      <div style={{ '--border': 'rgba(255,255,255,0.10)' } as React.CSSProperties}>
        <RingChart
          data={formattedData}
          hoveredIndex={hoveredIndex}
          onHoverChange={onHoverChange}
          size={size}
        >
          {formattedData.map((_, i) => (
            <Ring index={i} key={i} />
          ))}

          <RingCenter defaultLabel="Total" />
        </RingChart>
      </div>

      {/* Legend */}
      <Legend
        items={formattedData}
        hoveredIndex={hoveredIndex}
        onHoverChange={onHoverChange}
        prefix={prefix}
      >
        <LegendItemComponent>
          <LegendMarker />
          <LegendLabel />
          <LegendValue showPercentage />
          <LegendProgress />
        </LegendItemComponent>
      </Legend>
    </div>
  );
};
