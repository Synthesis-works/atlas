/**
 * LineChart — Declarative composite Line Chart
 */

import React, { createContext, useContext, useState } from 'react';
import { ChartPalette } from '../palette';
import type { ChartMargin } from '../types';

interface LineContextValue {
  data: any[];
  margin: ChartMargin;
  width: number;
  height: number;
  hoveredIdx: number | null;
  setHoveredIdx: (i: number | null) => void;
}

const LineContext = createContext<LineContextValue | null>(null);

function useLineChart() {
  const ctx = useContext(LineContext);
  if (!ctx) throw new Error('LineChart sub-components must be rendered inside <LineChart>');
  return ctx;
}

export interface LineChartProps {
  data: any[];
  margin?: ChartMargin;
  children: React.ReactNode;
  height?: number;
}

export const LineChart: React.FC<LineChartProps> = ({
  data,
  margin = { top: 8, right: 8, bottom: 40, left: 8 },
  children,
  height = 160,
}) => {
  const width = 360;
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  return (
    <LineContext.Provider value={{ data, margin, width, height, hoveredIdx, setHoveredIdx }}>
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
    </LineContext.Provider>
  );
};

export const Background: React.FC<{ pattern?: 'dots' | 'lines'; opacity?: number }> = ({
  pattern = 'dots',
  opacity = 0.85,
}) => {
  const { width, height } = useLineChart();

  if (pattern === 'dots') {
    return (
      <g opacity={opacity}>
        <pattern id="line-grid-dots" width="12" height="12" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r="1" fill="rgba(255,255,255,0.12)" />
        </pattern>
        <rect width={width} height={height} fill="url(#line-grid-dots)" />
      </g>
    );
  }

  return (
    <g opacity={opacity}>
      {[0.25, 0.5, 0.75].map((r) => (
        <line
          key={r}
          x1="0"
          y1={height * r}
          x2={width}
          y2={height * r}
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="1"
        />
      ))}
    </g>
  );
};

export interface LineProps {
  dataKey: string;
  strokeWidth?: number;
  color?: string;
}

export const Line: React.FC<LineProps> = ({
  dataKey,
  strokeWidth = 2,
  color = ChartPalette.accent,
}) => {
  const { data, width, height, margin, hoveredIdx } = useLineChart();
  if (!data.length) return null;

  const max = Math.max(...data.map((d) => Number(d[dataKey]) || 1), 1);
  const padL = margin.left ?? 8;
  const padR = margin.right ?? 8;
  const padT = margin.top ?? 8;
  const padB = margin.bottom ?? 40;

  const w = width - padL - padR;
  const h = height - padT - padB;

  const points = data.map((d, i) => {
    const x = padL + (i / (data.length - 1 || 1)) * w;
    const y = padT + h - ((Number(d[dataKey]) || 0) / max) * h;
    return { x, y };
  });

  const ptsStr = points.map((p) => `${p.x},${p.y}`).join(' ');

  return (
    <g>
      <polyline
        points={ptsStr}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {hoveredIdx !== null && points[hoveredIdx] && (
        <circle
          cx={points[hoveredIdx].x}
          cy={points[hoveredIdx].y}
          r="4"
          fill={color}
          stroke="#000"
          strokeWidth="2"
        />
      )}
    </g>
  );
};

export const XAxis: React.FC = () => {
  const { data, width, height, margin } = useLineChart();
  if (!data.length) return null;

  const padL = margin.left ?? 8;
  const padR = margin.right ?? 8;
  const w = width - padL - padR;
  const step = Math.ceil(data.length / 5);

  return (
    <g>
      {data.map((d, i) => {
        if (i % step !== 0 && i !== data.length - 1) return null;
        const x = padL + (i / (data.length - 1 || 1)) * w;
        const label = d.date ? new Date(d.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : d.month || `P${i}`;
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
            {label}
          </text>
        );
      })}
    </g>
  );
};

export const ChartTooltip: React.FC = () => {
  const { hoveredIdx, data } = useLineChart();
  if (hoveredIdx === null || !data[hoveredIdx]) return null;

  const item = data[hoveredIdx];

  return (
    <div className="absolute top-2 right-2 pointer-events-none rounded-lg p-2 bg-ink-3/90 border border-white/10 text-[10px] font-mono space-y-1 backdrop-blur-md z-20">
      <div className="text-white/40">{item.month || item.date || `Point ${hoveredIdx}`}</div>
      {Object.entries(item)
        .filter(([k]) => k !== 'month' && k !== 'date')
        .map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 text-white/80">
            <span className="capitalize">{k}:</span>
            <span className="font-semibold text-white">{String(v)}</span>
          </div>
        ))}
    </div>
  );
};
