/**
 * RadarChart — Declarative composite Radar (Spider) Chart
 *
 * <RadarChart data={radarData} metrics={metrics} size={250}>
 *   <RadarGrid />
 *   <RadarAxis />
 *   <RadarLabels />
 *   {radarData.map((item, index) => (
 *     <RadarArea index={index} key={item.label} />
 *   ))}
 * </RadarChart>
 */

import React, { createContext, useContext } from 'react';
import { ChartPalette } from '../palette';

export interface RadarItem {
  label: string;
  values: Record<string, number>;
  color?: string;
}

interface RadarContextValue {
  data: RadarItem[];
  metrics: string[];
  size: number;
  cx: number;
  cy: number;
  r: number;
  step: number;
}

const RadarContext = createContext<RadarContextValue | null>(null);

function useRadar() {
  const ctx = useContext(RadarContext);
  if (!ctx) throw new Error('Radar sub-components must be rendered inside <RadarChart>');
  return ctx;
}

export interface RadarChartProps {
  data: RadarItem[];
  metrics: string[];
  size?: number;
  children: React.ReactNode;
}

export const RadarChart: React.FC<RadarChartProps> = ({
  data,
  metrics,
  size = 250,
  children,
}) => {
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 28;
  const n = metrics.length || 1;
  const step = (2 * Math.PI) / n;

  return (
    <RadarContext.Provider value={{ data, metrics, size, cx, cy, r, step }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="mx-auto select-none">
        {children}
      </svg>
    </RadarContext.Provider>
  );
};

export const RadarGrid: React.FC<{ levels?: number[] }> = ({ levels = [0.25, 0.5, 0.75, 1] }) => {
  const { metrics, cx, cy, r, step } = useRadar();

  return (
    <g>
      {levels.map((level) => {
        const pts = metrics
          .map((_, i) => {
            const a = i * step - Math.PI / 2;
            return `${cx + level * r * Math.cos(a)},${cy + level * r * Math.sin(a)}`;
          })
          .join(' ');
        return (
          <polygon
            key={level}
            points={pts}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="1"
          />
        );
      })}
    </g>
  );
};

export const RadarAxis: React.FC = () => {
  const { metrics, cx, cy, r, step } = useRadar();

  return (
    <g>
      {metrics.map((_, i) => {
        const a = i * step - Math.PI / 2;
        return (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={cx + r * Math.cos(a)}
            y2={cy + r * Math.sin(a)}
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="1"
          />
        );
      })}
    </g>
  );
};

export const RadarLabels: React.FC = () => {
  const { metrics, cx, cy, r, step } = useRadar();

  return (
    <g>
      {metrics.map((m, i) => {
        const a = i * step - Math.PI / 2;
        const lx = cx + (r + 16) * Math.cos(a);
        const ly = cy + (r + 16) * Math.sin(a);
        return (
          <text
            key={m}
            x={lx}
            y={ly}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize="8"
            fill="rgba(255,255,255,0.4)"
            className="font-sans font-medium"
          >
            {m}
          </text>
        );
      })}
    </g>
  );
};

export const RadarArea: React.FC<{ index: number }> = ({ index }) => {
  const { data, metrics, cx, cy, r, step } = useRadar();
  const item = data[index];
  if (!item) return null;

  const color = item.color || ChartPalette.series[index % ChartPalette.series.length];

  const scorePts = metrics
    .map((m, i) => {
      const val = (item.values[m] ?? 0) / 100;
      const a = i * step - Math.PI / 2;
      return `${cx + val * r * Math.cos(a)},${cy + val * r * Math.sin(a)}`;
    })
    .join(' ');

  return (
    <g>
      <polygon
        points={scorePts}
        fill={color}
        fillOpacity="0.15"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      {metrics.map((m, i) => {
        const val = (item.values[m] ?? 0) / 100;
        const a = i * step - Math.PI / 2;
        const dx = cx + val * r * Math.cos(a);
        const dy = cy + val * r * Math.sin(a);
        return <circle key={m} cx={dx} cy={dy} r="2.5" fill={color} />;
      })}
    </g>
  );
};
