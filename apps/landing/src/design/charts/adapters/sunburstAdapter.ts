/**
 * Sunburst Data Adapter — Converts taxonomy maps into SunburstNode hierarchies.
 */

import type { SunburstNode } from '../Sunburst';

export function createSunburstHierarchy(
  rootName: string,
  categories: { name: string; items: string[] }[],
): SunburstNode {
  return {
    id: 'root',
    name: rootName,
    children: categories.map((cat, idx) => ({
      id: `cat-${idx}`,
      name: cat.name,
      children: cat.items.map((item, itemIdx) => ({
        id: `item-${idx}-${itemIdx}`,
        name: item,
        value: 10 + (itemIdx % 5) * 5,
      })),
    })),
  };
}
