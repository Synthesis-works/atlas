/**
 * Atlas Visualization System — Tokens
 * Visual constants for geometry, spacing, stroke weights, and Glass integration.
 */

export const ChartTokens = {
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
  },
  radii: {
    sm: '0.375rem',
    md: '0.75rem',
    lg: '1rem',
    xl: '1.5rem',
    full: '9999px',
  },
  strokeWidths: {
    subtle: 1,
    normal: 1.5,
    bold: 2,
    heavy: 3,
  },
  opacities: {
    grid: 0.06,
    axis: 0.12,
    hover: 0.15,
    areaFill: 0.25,
  },
  fontSizes: {
    tiny: 9,
    axis: 10,
    label: 11,
    legend: 12,
    header: 14,
  },
  glass: {
    blur: '16px',
    tooltipRadius: '12px',
    containerRadius: '16px',
  },
  limits: {
    maxHeatmapCells: 10000, // 100 x 100
    maxSunburstDepth: 5,
    maxRadarAxes: 12,
    maxRingSegments: 12,
    maxBars: 200,
    maxPoints: 5000,
  },
} as const;
