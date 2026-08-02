/**
 * ChartGrid & ChartAxis — SVG background grid lines and tick axes.
 */

import React from 'react';
import { ChartTokens } from '../tokens';

interface ChartGridProps {
  horizontal?: boolean;
  vertical?: boolean;
  pattern?: 'lines' | 'dots';
  opacity?: number;
  width?: number;
  height?: number;
  ticks?: number;
}

export const ChartGrid: React.FC<ChartGridProps> = ({
  horizontal = true,
  pattern = 'lines',
  opacity = ChartTokens.opacities.grid,
  width = 300,
  height = 150,
  ticks = 4,
}) => {
  if (pattern === 'dots') {
    return (
      <g opacity={opacity}>
        <pattern id="chart-grid-dots" width="16" height="16" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r="1.2" fill="#ffffff" />
        </pattern>
        <rect width="100%" height="100%" fill="url(#chart-grid-dots)" />
      </g>
    );
  }

  return (
    <g opacity={opacity}>
      {horizontal &&
        Array.from({ length: ticks }).map((_, i) => {
          const y = (i / (ticks - 1)) * (height - 30) + 15;
          return (
            <line
              key={i}
              x1="0"
              y1={y}
              x2={width}
              y2={y}
              stroke="#ffffff"
              strokeWidth="1"
              strokeDasharray="4 4"
            />
          );
        })}
    </g>
  );
};

export const ChartAxis: React.FC<{
  labels?: string[];
  height?: number;
  width?: number;
}> = ({ labels, height = 150, width = 300 }) => {
  if (!labels || labels.length === 0) return null;

  return (
    <g>
      {labels.map((label, i) => {
        const x = (i / (labels.length - 1 || 1)) * (width - 40) + 20;
        return (
          <text
            key={i}
            x={x}
            y={height - 4}
            fill="rgba(255,255,255,0.4)"
            fontSize="10"
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
