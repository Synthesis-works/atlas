/**
 * Shared Chart Theme
 * Single source of truth for all Atlas Charts.
 */
import { ChartTokens, TypographyTokens } from '@/design/tokens';

export const ChartTheme = {
  font: TypographyTokens.family.sans,
  colors: {
    grid: ChartTokens.colors.grid,
    background: ChartTokens.colors.background,
    text: ChartTokens.colors.text,
    tooltipBackground: '#171717',
    tooltipBorder: 'rgba(255, 255, 255, 0.1)',
    series: [
      ChartTokens.colors.series1,
      ChartTokens.colors.series2,
      ChartTokens.colors.series3,
      ChartTokens.colors.series4,
      ChartTokens.colors.series5,
    ]
  },
  spacing: {
    margin: { top: 20, right: 20, bottom: 40, left: 40 },
    tooltipPadding: '12px 16px',
  },
  animation: {
    duration: 1000,
    easing: 'ease-out-expo'
  },
  geometry: {
    strokeWidth: ChartTokens.geometry.strokeWidth,
    barRadius: ChartTokens.geometry.barRadius,
    pointRadius: ChartTokens.geometry.pointRadius,
  }
} as const;
