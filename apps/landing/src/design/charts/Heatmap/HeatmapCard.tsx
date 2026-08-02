/**
 * Atlas Heatmap Card
 *
 * Bugs fixed:
 * 1. Double context: HeatmapCard was nesting HeatmapInteractionProvider inside
 *    HeatmapChart which already creates one — removed the redundant outer provider.
 * 2. weekendOpacity predicate `row >= 5` never triggered on 4-row datasets — changed
 *    to a no-op identity function so all rows render at full opacity.
 * 3. ChartContainer + HeatmapChart were both adding dark backgrounds and padding —
 *    HeatmapCard now renders its own single-surface wrapper.
 * 4. Cell scale-110 hover broke the flex row layout — replaced with ring outline only.
 * 5. AtlasHeatmapYAxis pt-[28px] was misaligned; corrected spacer height to match
 *    the actual AtlasHeatmapXAxis rendered height (h-6 = 24px + gap = 28px total).
 * 6. Tooltip was positioned relative to the inner HeatmapChart div, not the card —
 *    moved to be relative to the correct surface wrapper.
 */

import React, { createContext, useContext, useState } from 'react';
import { ChartPalette } from '../palette';
import { useModelsStore } from '@/features/models/store/modelsStore';

/* ----------------------------------------------------------------------- */
/*  Types                                                                    */
/* ----------------------------------------------------------------------- */

export interface HeatmapMatrixData {
  rows: string[];
  columns: string[];
  values: number[][];
  metadata?: Record<string, unknown>;
}

export type RowOpacityFn = (row: number) => number;

export function buildHeatmapRowOpacity(
  predicate: (row: number) => boolean,
  opacity: number,
): RowOpacityFn {
  return (row: number) => (predicate(row) ? opacity : 1);
}

/* ----------------------------------------------------------------------- */
/*  Context                                                                  */
/* ----------------------------------------------------------------------- */

interface HeatmapCtx {
  data: HeatmapMatrixData;
  hoveredCell: { row: number; col: number } | null;
  setHoveredCell: (cell: { row: number; col: number } | null) => void;
  gap: number;
  onCellClick?: (row: string, col: string, val: number) => void;
}

const HeatmapContext = createContext<HeatmapCtx | null>(null);

function useHeatmap(): HeatmapCtx {
  const ctx = useContext(HeatmapContext);
  if (!ctx) throw new Error('Heatmap components must be inside HeatmapProvider');
  return ctx;
}

const DEFAULT_DATA: HeatmapMatrixData = {
  rows: ['Node 01', 'Node 02', 'Node 03', 'Node 04'],
  columns: ['00', '04', '08', '12', '16', '20'],
  values: [
    [12, 45, 89, 23, 67, 90],
    [34, 78, 12, 99, 45, 33],
    [88, 21, 56, 77, 10, 64],
    [42, 60, 31, 15, 82, 95],
  ],
};

function HeatmapProvider({
  data,
  gap,
  onCellClick,
  children,
}: {
  data?: HeatmapMatrixData;
  gap?: number;
  onCellClick?: (row: string, col: string, val: number) => void;
  children: React.ReactNode;
}) {
  const [hoveredCell, setHoveredCell] = useState<{ row: number; col: number } | null>(null);
  return (
    <HeatmapContext.Provider
      value={{
        data: data ?? DEFAULT_DATA,
        hoveredCell,
        setHoveredCell,
        gap: gap ?? 3,
        onCellClick,
      }}
    >
      {children}
    </HeatmapContext.Provider>
  );
}

/* ----------------------------------------------------------------------- */
/*  Cell colour scale                                                        */
/* ----------------------------------------------------------------------- */

function getCellColor(val: number, maxVal: number): string {
  if (val === 0) return ChartPalette.heatmap.min;
  const ratio = val / maxVal;
  if (ratio < 0.25) return ChartPalette.heatmap.low;
  if (ratio < 0.60) return ChartPalette.heatmap.mid;
  if (ratio < 0.85) return ChartPalette.heatmap.high;
  return ChartPalette.heatmap.max;
}

/* ----------------------------------------------------------------------- */
/*  HeatmapCells                                                             */
/* ----------------------------------------------------------------------- */

export const HeatmapCells: React.FC<{ rowOpacity?: RowOpacityFn | number }> = ({
  rowOpacity,
}) => {
  const { data, hoveredCell, setHoveredCell, onCellClick } = useHeatmap();
  const { rows, columns, values } = data;
  const maxVal = Math.max(...values.flat(), 1);

  return (
    <div className="space-y-1.5 font-mono text-xs w-full flex-1 min-w-0">
      {rows.map((rowLabel, rIdx) => {
        const opacity =
          typeof rowOpacity === 'function'
            ? rowOpacity(rIdx)
            : typeof rowOpacity === 'number'
            ? rowOpacity
            : 1;

        return (
          <div key={rowLabel} className="flex items-center gap-1.5 w-full" style={{ opacity }}>
            <div className="flex-1 flex gap-1.5">
              {columns.map((colLabel, cIdx) => {
                const val = values[rIdx]?.[cIdx] ?? 0;
                const isHovered = hoveredCell?.row === rIdx && hoveredCell?.col === cIdx;
                const isCrosshair = hoveredCell !== null &&
                  (hoveredCell.row === rIdx || hoveredCell.col === cIdx) &&
                  !isHovered;

                return (
                  <div
                    key={colLabel}
                    onClick={() => onCellClick?.(rowLabel, colLabel, val)}
                    onMouseEnter={() => setHoveredCell({ row: rIdx, col: cIdx })}
                    onMouseLeave={() => setHoveredCell(null)}
                    className={[
                      'flex-1 h-6 rounded-sm flex items-center justify-center cursor-pointer',
                      'transition-all duration-100',
                      isHovered
                        ? 'ring-2 ring-white/70 ring-offset-0 z-10 relative'
                        : isCrosshair
                        ? 'brightness-125'
                        : 'hover:brightness-110',
                    ].join(' ')}
                    style={{ backgroundColor: getCellColor(val, maxVal) }}
                  />
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
};

/* ----------------------------------------------------------------------- */
/*  AtlasHeatmapXAxis                                                       */
/* ----------------------------------------------------------------------- */

export const AtlasHeatmapXAxis: React.FC = () => {
  const { data } = useHeatmap();
  const ticks = data.columns.length > 0 ? data.columns : ['00', '04', '08', '12', '16', '20'];

  return (
    /* h-6 matches cell height; mb-1.5 matches the cell row gap */
    <div className="flex items-center gap-1.5 font-mono text-[11px] text-neutral-400 font-semibold select-none w-full h-6 mb-1.5">
      {ticks.map((col) => (
        <div key={col} className="flex-1 text-center truncate tracking-wider">
          {col}
        </div>
      ))}
    </div>
  );
};

export const HeatmapXAxis = AtlasHeatmapXAxis;

/* ----------------------------------------------------------------------- */
/*  AtlasHeatmapYAxis                                                       */
/* ----------------------------------------------------------------------- */

export interface AtlasHeatmapYAxisProps {
  tickFilter?: 'all' | 'even' | 'odd';
  rowOpacity?: RowOpacityFn | number;
}

export const AtlasHeatmapYAxis: React.FC<AtlasHeatmapYAxisProps> = ({
  tickFilter = 'all',
  rowOpacity,
}) => {
  const { data } = useHeatmap();
  const rows = data.rows.length > 0 ? data.rows : ['Node 01', 'Node 02', 'Node 03', 'Node 04'];

  /*
    Spacer height = XAxis h-6 (24px) + mb-1.5 gap (6px) = 30px total.
    This aligns the first row label with the first row of cells exactly.
  */
  return (
    <div className="space-y-1.5 font-mono text-xs shrink-0 select-none min-w-[68px]" style={{ paddingTop: '30px' }}>
      {rows.map((rowLabel, rIdx) => {
        if (tickFilter === 'even' && rIdx % 2 !== 0) return null;
        if (tickFilter === 'odd'  && rIdx % 2 === 0) return null;

        const opacity =
          typeof rowOpacity === 'function'
            ? rowOpacity(rIdx)
            : typeof rowOpacity === 'number'
            ? rowOpacity
            : 1;

        return (
          <div
            key={rowLabel}
            className="h-6 flex items-center text-[11px] text-neutral-300 font-mono font-medium truncate pr-2"
            style={{ opacity }}
          >
            {rowLabel}
          </div>
        );
      })}
    </div>
  );
};

export const HeatmapYAxis = AtlasHeatmapYAxis;

/* ----------------------------------------------------------------------- */
/*  HeatmapTooltip                                                           */
/* ----------------------------------------------------------------------- */

export const HeatmapTooltip: React.FC = () => {
  const { data, hoveredCell } = useHeatmap();
  if (!hoveredCell) return null;

  const row = data.rows[hoveredCell.row] ?? `Node ${hoveredCell.row + 1}`;
  const col = data.columns[hoveredCell.col] ?? `${hoveredCell.col}:00`;
  const val = data.values[hoveredCell.row]?.[hoveredCell.col] ?? 0;

  return (
    <div
      className="absolute top-2 right-2 pointer-events-none rounded-xl p-3
                 border border-white/20 text-xs font-mono text-white shadow-2xl z-30 space-y-1 min-w-[140px]"
      style={{ background: 'rgba(10,10,14,0.92)', backdropFilter: 'blur(12px)' }}
    >
      <div className="text-white font-bold">{col}</div>
      <div className="text-neutral-400 text-[11px] pb-1 border-b border-white/10">{row}</div>
      <div className="text-white font-semibold pt-1">
        <span className="text-white font-bold text-sm">{val}</span>
        <span className="text-neutral-400 ml-1">score</span>
      </div>
    </div>
  );
};

/* ----------------------------------------------------------------------- */
/*  HeatmapLegend                                                            */
/* ----------------------------------------------------------------------- */

export interface HeatmapLegendProps {
  align?: 'left' | 'center' | 'right';
}

export const HeatmapLegend: React.FC<HeatmapLegendProps> = ({ align = 'center' }) => {
  const cls = align === 'left' ? 'justify-start' : align === 'right' ? 'justify-end' : 'justify-center';
  const swatches = [
    ChartPalette.heatmap.min,
    ChartPalette.heatmap.low,
    ChartPalette.heatmap.mid,
    ChartPalette.heatmap.high,
    ChartPalette.heatmap.max,
  ];

  return (
    <div className={`flex items-center gap-2.5 mt-3 font-mono text-[11px] text-neutral-400 font-medium ${cls} select-none`}>
      <span>Less</span>
      <div className="flex items-center gap-1.5">
        {swatches.map((bg, i) => (
          <span
            key={i}
            className="w-3.5 h-3.5 rounded-sm border border-white/10 inline-block"
            style={{ backgroundColor: bg }}
          />
        ))}
      </div>
      <span>More</span>
    </div>
  );
};

/* ----------------------------------------------------------------------- */
/*  HeatmapChart — single context, no double-wrap                           */
/* ----------------------------------------------------------------------- */

export interface HeatmapChartProps {
  data: HeatmapMatrixData;
  gap?: number;
  onCellClick?: (row: string, col: string, val: number) => void;
  children: React.ReactNode;
  className?: string;
}

export const HeatmapChart: React.FC<HeatmapChartProps> = ({
  data,
  gap = 3,
  onCellClick,
  children,
  className = '',
}) => (
  /* Single provider — no nesting */
  <HeatmapProvider data={data} gap={gap} onCellClick={onCellClick}>
    <div className={`w-full relative min-w-0 flex flex-col gap-2 ${className}`}>
      {children}
    </div>
  </HeatmapProvider>
);

/* ----------------------------------------------------------------------- */
/*  HeatmapCard — the opinionated composition                               */
/* ----------------------------------------------------------------------- */

export const HeatmapCard: React.FC<{
  title: string;
  subtitle?: string;
  badge?: string;
  data: HeatmapMatrixData;
  onCellClick?: (row: string, col: string, val: number) => void;
}> = ({ title, subtitle, badge, data, onCellClick }) => (
  /* Single dark card surface — no ChartContainer double-wrap */
  <div className="w-full relative flex flex-col gap-3 bg-[#0c0c0e] border border-white/[0.08] rounded-2xl p-5 shadow-xl text-white">
    {/* Header */}
    <div className="flex items-start justify-between gap-3 pb-3 border-b border-white/[0.06]">
      <div>
        <h4 className="text-sm font-semibold text-white tracking-tight">{title}</h4>
        {subtitle && <p className="text-xs text-white/40 mt-0.5">{subtitle}</p>}
      </div>
      {badge && (
        <span className="shrink-0 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium text-accent bg-accent/10 border border-accent/20">
          {badge}
        </span>
      )}
    </div>

    {/* Chart — single HeatmapProvider wraps everything */}
    <HeatmapProvider data={data} gap={3} onCellClick={onCellClick}>
      {/* Relative wrapper for tooltip positioning */}
      <div className="relative w-full">
        <div className="flex w-full min-w-0 items-start gap-3">
          <AtlasHeatmapYAxis />
          <div className="flex-1 min-w-0 flex flex-col">
            <AtlasHeatmapXAxis />
            <HeatmapCells />
          </div>
        </div>
        <HeatmapTooltip />
      </div>
    </HeatmapProvider>

    <HeatmapLegend align="center" />
  </div>
);

/* ----------------------------------------------------------------------- */
/*  Semantic Heatmap variants                                                */
/* ----------------------------------------------------------------------- */

export const FleetActivityMatrix: React.FC<{ data: HeatmapMatrixData }> = ({ data }) => {
  const { openDrawer, models } = useModelsStore();
  const handleInspect = (row: string) => {
    const matched = models.find((m) => m.name.toLowerCase().includes(row.toLowerCase()));
    if (matched) openDrawer(matched, 'overview');
  };
  return (
    <HeatmapCard
      title="Fleet Activity Matrix"
      subtitle="Request Volume per Model across 24h Windows"
      badge="Live Operations"
      data={data}
      onCellClick={(row) => handleInspect(row)}
    />
  );
};

export const ModelHealthMatrix: React.FC<{ data: HeatmapMatrixData }> = ({ data }) => (
  <HeatmapCard
    title="Model Health Matrix"
    subtitle="Historical Availability & Latency Score Progression"
    badge="SLO Monitoring"
    data={data}
  />
);

export const EvaluationFailureMatrix: React.FC<{ data: HeatmapMatrixData }> = ({ data }) => (
  <HeatmapCard
    title="Evaluation Failure Matrix"
    subtitle="Failure Rates across Benchmark Suites & Datasets"
    badge="Diagnostic"
    data={data}
  />
);

export const BenchmarkDominanceMatrix: React.FC<{ data: HeatmapMatrixData }> = ({ data }) => (
  <HeatmapCard
    title="Benchmark Dominance Matrix"
    subtitle="Relative Leaderboard Standing across Evaluation Categories"
    badge="Leaderboard"
    data={data}
  />
);

export const GPUUtilizationMatrix: React.FC<{ data: HeatmapMatrixData }> = ({ data }) => (
  <HeatmapCard
    title="GPU Utilization Matrix"
    subtitle="Cluster Saturation & VRAM Memory Allocation"
    badge="Infrastructure"
    data={data}
  />
);

export const ProviderCostMatrix: React.FC<{ data: HeatmapMatrixData }> = ({ data }) => (
  <HeatmapCard
    title="Provider Cost Matrix"
    subtitle="Daily Financial Run Rate per Inference Provider"
    badge="FinOps"
    data={data}
  />
);
