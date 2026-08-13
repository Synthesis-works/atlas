import React from 'react';

import { AtlasPieChart } from '@/components/atlas/charts';

export type ChartType = 'donut' | 'bar' | 'stacked-bar' | 'line';

export interface ChartDataItem {
  label: string;
  value: number;
  color?: string;
  secondaryValue?: number;
}

export interface ChartConfig {
  type: ChartType;
  data: ChartDataItem[];
  height?: number;
}

export const ChartRenderer: React.FC<ChartConfig> = ({ type, data, height = 140 }) => {
  if (!data || data.length === 0) {
    return <div className="text-xs text-white/20 font-mono">No data points available</div>;
  }

  const COLORS = ['#34d399', '#a78bfa', '#60a5fa', '#f59e0b', '#f43f5e', '#38bdf8'];

  if (type === 'donut') {
    const pieData = data.map(d => ({
      label: d.label,
      value: d.value
    }));

    return (
      <div className="flex items-center gap-6 w-full py-2">
        <div className="shrink-0 flex items-center justify-center">
          <AtlasPieChart 
            data={pieData}
            size={96}
            innerRadius={30}
            hoverEffect="grow"
          />
        </div>

        <div className="flex-1 space-y-1.5 font-mono text-[11px]">
          {pieData.map((item, idx) => (
            <div key={item.label} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-sm shrink-0"
                  style={{ backgroundColor: `var(--chart-${(idx % 5) + 1})` }}
                />
                <span className="text-white/60 truncate max-w-[100px]" title={item.label}>{item.label}</span>
              </div>
              <span className="text-white font-medium">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (type === 'bar') {
    const maxValue = Math.max(...data.map((d) => d.value), 1);

    return (
      <div className="w-full space-y-2 py-1 font-mono text-xs">
        {data.map((item, idx) => {
          const pct = (item.value / maxValue) * 100;
          const color = item.color || COLORS[idx % COLORS.length];

          return (
            <div key={item.label} className="space-y-1">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-white/60">{item.label}</span>
                <span className="text-white">{item.value} ms</span>
              </div>
              <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${pct}%`, backgroundColor: color }}
                />
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  if (type === 'stacked-bar') {
    const total = data.reduce((acc, d) => acc + d.value + (d.secondaryValue || 0), 0);

    return (
      <div className="w-full space-y-3 py-2 font-mono text-xs">
        <div className="w-full h-4 rounded-lg bg-white/5 flex overflow-hidden">
          {data.map((item, idx) => {
            const pct = (item.value / total) * 100;
            return (
              <div
                key={item.label}
                className="h-full transition-all duration-500"
                style={{
                  width: `${pct}%`,
                  backgroundColor: item.color || COLORS[idx % COLORS.length],
                }}
              />
            );
          })}
        </div>
        <div className="flex flex-wrap gap-4 text-[11px]">
          {data.map((item, idx) => (
            <div key={item.label} className="flex items-center gap-1.5">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: item.color || COLORS[idx % COLORS.length] }}
              />
              <span className="text-white/60">{item.label}:</span>
              <span className="text-white font-medium">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Fallback: line chart (SVG path)
  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const points = data
    .map((d, i) => {
      const x = (i / (data.length - 1 || 1)) * 260 + 10;
      const y = height - (d.value / maxVal) * (height - 30) - 15;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div className="w-full py-1">
      <svg width="100%" height={height} viewBox={`0 0 280 ${height}`} className="overflow-visible">
        <polyline
          fill="none"
          stroke="#60a5fa"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={points}
        />
        {data.map((d, i) => {
          const x = (i / (data.length - 1 || 1)) * 260 + 10;
          const y = height - (d.value / maxVal) * (height - 30) - 15;
          return (
            <g key={i} className="group">
              <circle cx={x} cy={y} r="3" fill="#60a5fa" className="transition-all group-hover:r-5" />
              <text x={x} y={y - 8} fill="#94a3b8" fontSize="9" textAnchor="middle" className="font-mono">
                {d.value}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

export default ChartRenderer;
