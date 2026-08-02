/**
 * BarChart — Declarative composite Grouped Bar Chart
 */

import React, { createContext, useContext, useState } from 'react';
import { ChartPalette } from '../palette';
import type { ChartMargin } from '../types';

interface BarContextValue {
  data: any[];
  xDataKey: string;
  margin: ChartMargin;
  width: number;
  height: number;
  bars: { dataKey: string; fill: string; lineCap?: 'round' | 'square' }[];
  registerBar: (bar: { dataKey: string; fill: string; lineCap?: 'round' | 'square' }) => void;
  hoveredIdx: number | null;
  setHoveredIdx: (i: number | null) => void;
}

const BarContext = createContext<BarContextValue | null>(null);

function useBarChart() {
  const ctx = useContext(BarContext);
  if (!ctx) throw new Error('BarChart sub-components must be inside <BarChart>');
  return ctx;
}

export interface BarChartProps {
  data: any[];
  xDataKey: string;
  margin?: ChartMargin;
  children: React.ReactNode;
  height?: number;
}

export const BarChart: React.FC<BarChartProps> = ({
  data,
  xDataKey,
  margin = { top: 8, right: 8, bottom: 40, left: 8 },
  children,
  height = 160,
}) => {
  const width = 360;
  const [bars, setBars] = useState<{ dataKey: string; fill: string; lineCap?: 'round' | 'square' }[]>([]);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const registerBar = (bar: { dataKey: string; fill: string; lineCap?: 'round' | 'square' }) => {
    setBars((prev) => {
      if (prev.some((b) => b.dataKey === bar.dataKey)) return prev;
      return [...prev, bar];
    });
  };

  return (
    <BarContext.Provider
      value={{ data, xDataKey, margin, width, height, bars, registerBar, hoveredIdx, setHoveredIdx }}
    >
      <div className="w-full relative select-none">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full overflow-visible"
          onPointerMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const ratio = (e.clientX - rect.left) / rect.width;
            const idx = Math.min(Math.max(Math.floor(ratio * data.length), 0), data.length - 1);
            setHoveredIdx(idx);
          }}
          onPointerLeave={() => setHoveredIdx(null)}
        >
          {children}
        </svg>
      </div>
    </BarContext.Provider>
  );
};

export const Grid: React.FC<{ horizontal?: boolean }> = ({ horizontal = true }) => {
  const { width, height, margin } = useBarChart();
  if (!horizontal) return null;

  const padB = margin.bottom ?? 40;
  const h = height - padB;

  return (
    <g opacity={0.06}>
      {[0.25, 0.5, 0.75].map((r) => (
        <line
          key={r}
          x1="0"
          y1={h * r}
          x2={width}
          y2={h * r}
          stroke="#ffffff"
          strokeWidth="1"
          strokeDasharray="4 4"
        />
      ))}
    </g>
  );
};

export interface BarProps {
  dataKey: string;
  fill?: string;
  lineCap?: 'round' | 'square';
}

export const Bar: React.FC<BarProps> = ({
  dataKey,
  fill = ChartPalette.accent,
  lineCap = 'square',
}) => {
  const { data, width, height, margin, bars, registerBar } = useBarChart();

  React.useEffect(() => {
    registerBar({ dataKey, fill, lineCap });
  }, [dataKey, fill, lineCap]);

  if (!data.length) return null;

  const max = Math.max(...data.map((d) => Number(d[dataKey]) || 1), 1);
  const padL = margin.left ?? 8;
  const padR = margin.right ?? 8;
  const padB = margin.bottom ?? 40;
  const w = width - padL - padR;
  const h = height - padB;

  const groupWidth = w / data.length;
  const barCount = bars.length || 1;
  const barWidth = Math.max((groupWidth - 8) / barCount, 4);
  const barIdx = bars.findIndex((b) => b.dataKey === dataKey);

  return (
    <g>
      {data.map((d, i) => {
        const val = Number(d[dataKey]) || 0;
        const barH = (val / max) * h;
        const x = padL + i * groupWidth + (barIdx >= 0 ? barIdx * barWidth : 0) + 4;
        const y = h - barH;
        const rx = lineCap === 'round' ? 4 : 0;

        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={barWidth}
            height={barH}
            fill={fill}
            rx={rx}
            ry={rx}
            className="transition-all duration-300 hover:opacity-80"
          />
        );
      })}
    </g>
  );
};

export const BarXAxis: React.FC = () => {
  const { data, xDataKey, width, height, margin } = useBarChart();
  if (!data.length) return null;

  const padL = margin.left ?? 8;
  const padR = margin.right ?? 8;
  const w = width - padL - padR;
  const groupWidth = w / data.length;

  return (
    <g>
      {data.map((d, i) => {
        const x = padL + i * groupWidth + groupWidth / 2;
        return (
          <text
            key={i}
            x={x}
            y={height - 12}
            fill="rgba(255,255,255,0.4)"
            fontSize="9"
            textAnchor="middle"
            className="font-mono select-none"
          >
            {String(d[xDataKey] ?? `P${i}`)}
          </text>
        );
      })}
    </g>
  );
};

export const ChartTooltip: React.FC = () => {
  const { hoveredIdx, data, xDataKey } = useBarChart();
  if (hoveredIdx === null || !data[hoveredIdx]) return null;

  const item = data[hoveredIdx];

  return (
    <div className="absolute top-2 right-2 pointer-events-none rounded-lg p-2 bg-ink-3/90 border border-white/10 text-[10px] font-mono space-y-1 backdrop-blur-md z-20">
      <div className="text-white/40">{String(item[xDataKey] || `Index ${hoveredIdx}`)}</div>
      {Object.entries(item)
        .filter(([k]) => k !== xDataKey)
        .map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 text-white/80">
            <span className="capitalize">{k}:</span>
            <span className="font-semibold text-white">{String(v)}</span>
          </div>
        ))}
    </div>
  );
};
