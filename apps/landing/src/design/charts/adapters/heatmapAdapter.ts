/**
 * Heatmap Data Adapter — Normalizes domain structures into HeatmapMatrixData.
 */

import type { HeatmapMatrixData } from '../Heatmap';

export function createHeatmapData(
  rows: string[],
  columns: string[],
  generator?: (r: string, c: string) => number,
): HeatmapMatrixData {
  const values = rows.map((r) =>
    columns.map((c) => (generator ? generator(r, c) : Math.floor(Math.random() * 100))),
  );

  return { rows, columns, values };
}
