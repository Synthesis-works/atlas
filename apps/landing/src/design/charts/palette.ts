/**
 * Atlas Visualization System — Palette
 * Color ramps and category color bridges matching Atlas design tokens.
 */

export const ChartPalette = {
  accent: '#6366f1',
  accentHover: '#818cf8',
  success: '#34d399',
  warning: '#fbbf24',
  danger: '#ef4444',
  info: '#38bdf8',

  categories: {
    models: '#818cf8',       // indigo
    benchmarks: '#67e8f9',   // cyan
    capabilities: '#a78bfa', // violet
    safety: '#f472b6',       // pink
    data: '#34d399',         // emerald
    output: '#fbbf24',       // amber
  },

  series: [
    '#6366f1', // Indigo
    '#67e8f9', // Cyan
    '#34d399', // Emerald
    '#a78bfa', // Violet
    '#fbbf24', // Amber
    '#f472b6', // Pink
    '#38bdf8', // Sky Blue
    '#f97316', // Orange
  ],

  // High-Contrast Monochrome Black, White & Grey Heatmap Scale (Guarantees visible cell tiles on dark surfaces)
  heatmap: {
    min: '#1e1e26', // Distinct visible dark tile (never pitch-black or blended with #0c0c0e background)
    low: '#363642',
    mid: '#626272',
    high: '#a0a0b0',
    max: '#ffffff',
  },

  ink: {
    bg: 'var(--color-ink-2)',
    surface: 'var(--color-ink-3)',
    border: 'var(--color-border)',
    textPrimary: 'var(--color-text-primary)',
    textSecondary: 'var(--color-text-secondary)',
    textMuted: 'var(--color-text-tertiary)',
  },
} as const;
