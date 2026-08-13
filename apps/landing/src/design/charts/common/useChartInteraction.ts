/**
 * useChartInteraction — shared interaction hook
 * Tracks hovered index, pointer coordinates, and keyboard navigation.
 */

import { useState, useCallback } from 'react';

export function useChartInteraction() {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [pointerPos, setPointerPos] = useState<{ x: number; y: number } | null>(null);

  const handlePointerMove = useCallback((e: React.PointerEvent<SVGElement | HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setPointerPos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  }, []);

  const handlePointerLeave = useCallback(() => {
    setHoveredIndex(null);
    setPointerPos(null);
  }, []);

  return {
    hoveredIndex,
    setHoveredIndex,
    pointerPos,
    handlePointerMove,
    handlePointerLeave,
  };
}
