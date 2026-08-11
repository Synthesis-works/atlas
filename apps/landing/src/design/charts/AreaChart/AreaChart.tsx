/**
 * AreaChart — Declarative composite Area Chart
 */

import React, { createContext, useContext, useState } from 'react';
import { ChartPalette } from '../palette';

interface AreaContextValue {
  data: any[];
  aspectRatio?: string;
  width: number;
  height: number;
  hoveredIdx: number | null;
  setHoveredIdx: (idx: number | null) => void;
  mouseX: number | null;
  setMouseX: (x: number | null) => void;
}

const AreaContext = createContext<AreaContextValue | null>(null);

function useAreaChart() {
  const ctx = useContext(AreaContext);
  if (!ctx) throw new Error('AreaChart sub-components must be rendered inside <AreaChart>');
  return ctx;
}

export interface AreaChartProps {
  data: any[];
  aspectRatio?: string;
  children: React.ReactNode;
}

export const AreaChart: React.FC<AreaChartProps> = ({
  data,
  aspectRatio = '4 / 1',
  children,
}) => {
  const width = 400;
  const height = 100;
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const [mouseX, setMouseX] = useState<number | null>(null);

  const handlePointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = e.clientX - rect.left;
    const ratio = relX / rect.width;
    const idx = Math.min(Math.max(Math.floor(ratio * data.length), 0), data.length - 1);
    setHoveredIdx(idx);
    setMouseX(relX);
  };

  return (
    <AreaContext.Provider
      value={{ data, aspectRatio, width, height, hoveredIdx, setHoveredIdx, mouseX, setMouseX }}
    >
      <div style={{ aspectRatio }} className="w-full relative select-none">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full overflow-visible"
          onPointerMove={handlePointerMove}
          onPointerLeave={() => {
            setHoveredIdx(null);
            setMouseX(null);
          }}
        >
          {children}
        </svg>
      </div>
    </AreaContext.Provider>
  );
};

export const Grid: React.FC<{ horizontal?: boolean }> = ({ horizontal = true }) => {
  const { width, height } = useAreaChart();
  if (!horizontal) return null;

  return (
    <g opacity={0.06}>
      {[0.2, 0.4, 0.6, 0.8].map((ratio) => (
        <line
          key={ratio}
          x1="0"
          y1={height * ratio}
          x2={width}
          y2={height * ratio}
          stroke="#ffffff"
          strokeWidth="1"
          strokeDasharray="4 4"
        />
      ))}
    </g>
  );
};

export interface AreaProps {
  dataKey: string;
  fill?: string;
  fillOpacity?: number;
  strokeWidth?: number;
  curve?: any;
}

export const Area: React.FC<AreaProps> = ({
  dataKey,
  fill = ChartPalette.accent,
  fillOpacity = 0.25,
  strokeWidth = 2,
}) => {
  const { data, width, height } = useAreaChart();
  if (!data || data.length === 0) return null;

  const max = Math.max(...data.map((d) => Number(d[dataKey]) || 1), 1);
  const pad = 12;

  const points = data.map((d, i) => {
    const x = (i / (data.length - 1 || 1)) * (width - pad * 2) + pad;
    const y = height - pad - ((Number(d[dataKey]) || 0) / max) * (height - pad * 2);
    return { x, y };
  });

  const pathD = points.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`, '');
  const areaD = `${pathD} L ${width - pad},${height - pad} L ${pad},${height - pad} Z`;

  return (
    <g>
      <path d={areaD} fill={fill} fillOpacity={fillOpacity} />
      <path
        d={pathD}
        fill="none"
        stroke={fill}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </g>
  );
};

export const SegmentBackground: React.FC = () => {
  const { hoveredIdx, data, width, height } = useAreaChart();
  if (hoveredIdx === null || !data.length) return null;

  const x = (hoveredIdx / (data.length - 1 || 1)) * (width - 24) + 12;
  const colW = width / data.length;

  return (
    <rect
      x={x - colW / 2}
      y="0"
      width={colW}
      height={height}
      fill="rgba(255, 255, 255, 0.04)"
      className="pointer-events-none"
    />
  );
};

export const SegmentLineFrom: React.FC = () => {
  const { hoveredIdx, data, width, height } = useAreaChart();
  if (hoveredIdx === null || !data.length) return null;

  const x = (hoveredIdx / (data.length - 1 || 1)) * (width - 24) + 12;

  return (
    <line
      x1={x}
      y1="0"
      x2={x}
      y2={height}
      stroke="rgba(255, 255, 255, 0.15)"
      strokeWidth="1"
      strokeDasharray="2 2"
      className="pointer-events-none"
    />
  );
};

export const SegmentLineTo: React.FC = () => <SegmentLineFrom />;

export const XAxis: React.FC = () => {
  const { data, width, height } = useAreaChart();
  if (!data.length) return null;

  const step = Math.ceil(data.length / 5);

  return (
    <g>
      {data.map((d, i) => {
        if (i % step !== 0 && i !== data.length - 1) return null;
        const x = (i / (data.length - 1 || 1)) * (width - 24) + 12;
        const label = d.date ? new Date(d.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : `P${i}`;
        return (
          <text
            key={i}
            x={x}
            y={height + 10}
            fill="rgba(255,255,255,0.35)"
            fontSize="8"
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
  const { hoveredIdx, data } = useAreaChart();
  if (hoveredIdx === null || !data[hoveredIdx]) return null;

  const item = data[hoveredIdx];

  return (
    <div className="absolute top-2 right-2 pointer-events-none rounded-lg p-2 bg-ink-3/90 border border-white/10 text-[10px] font-mono space-y-1 backdrop-blur-md z-20">
      <div className="text-white/40">{item.date ? new Date(item.date).toDateString() : `Index ${hoveredIdx}`}</div>
      {Object.entries(item)
        .filter(([k]) => k !== 'date')
        .map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 text-white/80">
            <span className="capitalize">{k}:</span>
            <span className="font-semibold text-white">{String(v)}</span>
          </div>
        ))}
    </div>
  );
};
