import { LineChart } from '@/components/charts/line-chart';
import { Background, type BackgroundPatternPreset } from '@/components/charts/background';
import { Line } from '@/components/charts/line';
import { XAxis } from '@/components/charts/x-axis';
import { ChartTooltip } from '@/components/charts/tooltip/chart-tooltip';
import type { LineSeries, ChartBaseProps } from '../models/chart-models';

export interface AtlasLineChartProps extends ChartBaseProps {
  series?: LineSeries[];
  /** The time-series or categorical data array */
  data: Record<string, any>[];
  /** The key in the data objects to plot on the Y-axis */
  dataKey?: string;
  /** The background pattern preset to use */
  pattern?: BackgroundPatternPreset;
  /** The opacity of the background pattern */
  opacity?: number;
  /** The stroke width of the line */
  strokeWidth?: number;
  /** Margin for the chart layout */
  margin?: { top: number; right: number; bottom: number; left: number };
}

export function AtlasLineChart({
  series,
  data,
  dataKey = "desktop",
  pattern = "dots",
  opacity = 0.85,
  strokeWidth = 2,
  margin = { top: 8, right: 8, bottom: 40, left: 8 }
}: AtlasLineChartProps) {
  return (
    <LineChart margin={margin} data={data}>
      <Background pattern={pattern} opacity={opacity} />
      {series ? series.map(s => (
        <Line key={s.id} dataKey={s.id || dataKey} strokeWidth={strokeWidth} />
      )) : (
        <Line dataKey={dataKey} strokeWidth={strokeWidth} />
      )}
      <XAxis />
      <ChartTooltip />
    </LineChart>
  );
}
