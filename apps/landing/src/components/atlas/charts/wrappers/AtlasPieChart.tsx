
import { PieChart } from "@/components/charts/pie-chart";
import { PieSlice } from "@/components/charts/pie-slice";
import { PieCenter } from "@/components/charts/pie-center";
import { cn } from "@/lib/utils";
import type { PieSeries, ChartBaseProps } from '../models/chart-models';

export interface AtlasPieChartProps extends ChartBaseProps {
  data: PieSeries[];
  size?: number;
  innerRadius?: number;
  centerLabel?: string;
  hoverEffect?: "grow" | "none";
  title?: string;
  description?: string;
  loading?: boolean;
  emptyMessage?: string;
  className?: string;
  showLegend?: boolean;
}

export function AtlasPieChart({
  data,
  size = 200,
  innerRadius = 55,
  centerLabel,
  hoverEffect = "grow",
  title,
  description,
  loading,
  emptyMessage,
  className,
  showLegend
}: AtlasPieChartProps) {
  
  if (loading) {
    return (
      <div className={cn("flex flex-col items-center justify-center space-y-2 opacity-50", className)}>
        <div className="text-xs text-white/50 font-mono">Loading chart...</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className={cn("flex flex-col items-center justify-center space-y-2 opacity-50", className)}>
        <div className="text-xs text-white/50 font-mono">{emptyMessage || "No data available"}</div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col", className)}>
      {(title || description) && (
        <div className="mb-4">
          {title && <h4 className="text-sm font-semibold text-white">{title}</h4>}
          {description && <p className="text-xs text-white/50 mt-1">{description}</p>}
        </div>
      )}
      <div className="flex-1 flex flex-col md:flex-row items-center justify-center min-h-0 gap-6">
        <PieChart
          data={data}
          innerRadius={innerRadius}
          size={size}
        >
          {data.map((item, index) => (
            <PieSlice
              key={`${item.label}-${index}`}
              index={index}
              hoverEffect={hoverEffect}
            />
          ))}
          {centerLabel && <PieCenter defaultLabel={centerLabel} />}
        </PieChart>
        
        {showLegend && (
          <div className="space-y-2.5 flex-1 w-full max-w-[200px]">
            {data.map((item, i) => (
              <div key={item.label} className="flex items-center gap-2">
                <span 
                  className="w-2.5 h-2.5 rounded-sm flex-shrink-0" 
                  style={{ backgroundColor: `var(--chart-${(i % 5) + 1})` }} 
                />
                <span className="text-xs font-mono text-white/60 truncate">{item.label}</span>
                <span className="ml-auto text-xs font-mono text-white font-medium tabular-nums">{item.value}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
