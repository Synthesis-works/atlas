/**
 * Atlas Visualization System — Registry
 * Central map registering available visualization components and plugins.
 */

export const VisualizationRegistry = {
  area: 'AreaChart',
  line: 'LineChart',
  bar: 'BarChart',
  ring: 'RingChart',
  radar: 'RadarChart',
  heatmap: 'HeatmapCard',
  sunburst: 'SunburstCard',
  timeline: 'TimelineChart',
} as const;

export type VisualizationKey = keyof typeof VisualizationRegistry;
