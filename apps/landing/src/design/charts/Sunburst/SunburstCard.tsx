/**
 * SunburstCard & SunburstChart — Radial Hierarchy Explorer
 *
 * <SunburstChart data={data} size={460}>
 *   <SunburstBreadcrumb>
 *     <SunburstDrillBreadcrumb />
 *   </SunburstBreadcrumb>
 *   {arcs.map((arc) => (
 *     <SunburstSegment index={arc.arcIndex} key={arc.id} />
 *   ))}
 *   <SunburstCenter />
 *   <SunburstLabels />
 *   <SunburstHint />
 * </SunburstChart>
 */

import React, { createContext, useContext, useState } from 'react';
import { ChartContainer, ChartHeader, ChartBody } from '../common';
import { ChartPalette } from '../palette';

export interface SunburstNode {
  id: string;
  name: string;
  value?: number;
  color?: string;
  children?: SunburstNode[];
}

interface SunburstContextValue {
  data: SunburstNode;
  activeNode: SunburstNode;
  breadcrumbs: SunburstNode[];
  zoomTo: (node: SunburstNode) => void;
  hoveredNode: SunburstNode | null;
  setHoveredNode: (node: SunburstNode | null) => void;
  size: number;
  arcs: { id: string; name: string; arcIndex: number; color: string; val: number }[];
}

const SunburstContext = createContext<SunburstContextValue | null>(null);

function useSunburst() {
  const ctx = useContext(SunburstContext);
  if (!ctx) throw new Error('Sunburst sub-components must be inside <SunburstChart>');
  return ctx;
}

export interface SunburstChartProps {
  data: SunburstNode;
  size?: number;
  children: React.ReactNode;
}

export const SunburstChart: React.FC<SunburstChartProps> = ({
  data,
  size = 320,
  children,
}) => {
  const [activeNode, setActiveNode] = useState<SunburstNode>(data);
  const [breadcrumbs, setBreadcrumbs] = useState<SunburstNode[]>([data]);
  const [hoveredNode, setHoveredNode] = useState<SunburstNode | null>(null);

  const zoomTo = (node: SunburstNode) => {
    setActiveNode(node);
    const path: SunburstNode[] = [];
    const findPath = (curr: SunburstNode, target: SunburstNode, currentPath: SunburstNode[]): boolean => {
      const newPath = [...currentPath, curr];
      if (curr.id === target.id) {
        path.push(...newPath);
        return true;
      }
      if (curr.children) {
        for (const child of curr.children) {
          if (findPath(child, target, newPath)) return true;
        }
      }
      return false;
    };
    findPath(data, node, []);
    setBreadcrumbs(path.length ? path : [data]);
  };

  const childrenNodes = activeNode.children || [];
  const arcs = childrenNodes.map((child, idx) => ({
    id: child.id,
    name: child.name,
    arcIndex: idx,
    color: child.color || ChartPalette.series[idx % ChartPalette.series.length],
    val: child.value || (child.children?.length ?? 1) * 10,
  }));

  return (
    <SunburstContext.Provider
      value={{ data, activeNode, breadcrumbs, zoomTo, hoveredNode, setHoveredNode, size, arcs }}
    >
      <div className="flex flex-col items-center select-none space-y-3 w-full">
        {children}
      </div>
    </SunburstContext.Provider>
  );
};

export const SunburstBreadcrumb: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { breadcrumbs, zoomTo } = useSunburst();
  return (
    <div className="flex items-center gap-1 text-[11px] font-mono text-white/50 flex-wrap">
      {breadcrumbs.map((b, i) => (
        <React.Fragment key={b.id}>
          {i > 0 && <span className="text-white/20">/</span>}
          <button
            onClick={() => zoomTo(b)}
            className={`hover:text-accent transition-colors ${
              i === breadcrumbs.length - 1 ? 'text-white font-semibold' : ''
            }`}
          >
            {b.name}
          </button>
        </React.Fragment>
      ))}
      {children}
    </div>
  );
};

export const SunburstDrillBreadcrumb: React.FC = () => null;

export const SunburstSegment: React.FC<{ index: number }> = ({ index }) => {
  const { arcs, activeNode, zoomTo, setHoveredNode, size } = useSunburst();
  const arc = arcs[index];
  if (!arc) return null;

  const totalVal = arcs.reduce((s, a) => s + a.val, 0) || 1;
  let cumulativeAngle = 0;
  for (let i = 0; i < index; i++) {
    cumulativeAngle += arcs[i].val / totalVal;
  }
  const pct = arc.val / totalVal;

  const childNode = activeNode.children?.[index];

  return (
    <circle
      cx={size / 2}
      cy={size / 2}
      r={size / 3}
      fill="transparent"
      stroke={arc.color}
      strokeWidth={24}
      strokeDasharray={`${pct * (2 * Math.PI * (size / 3))} ${2 * Math.PI * (size / 3)}`}
      strokeDashoffset={-cumulativeAngle * (2 * Math.PI * (size / 3))}
      onClick={() => childNode && zoomTo(childNode)}
      onMouseEnter={() => childNode && setHoveredNode(childNode)}
      onMouseLeave={() => setHoveredNode(null)}
      className="transition-all duration-300 cursor-pointer hover:opacity-80"
    />
  );
};

export const SunburstCenter: React.FC = () => {
  const { activeNode, hoveredNode } = useSunburst();
  const display = hoveredNode || activeNode;

  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none p-4">
      <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider truncate max-w-[100px]">
        {display.name}
      </span>
      <span className="text-xs font-bold text-white font-mono mt-0.5">
        {display.children?.length ? `${display.children.length} items` : display.value ?? '100%'}
      </span>
    </div>
  );
};

export const SunburstLabels: React.FC = () => null;
export const SunburstHint: React.FC = () => (
  <p className="text-[10px] font-mono text-white/30 text-center">Click segments to drill down into hierarchy</p>
);

export const SunburstCard: React.FC<{
  title: string;
  subtitle?: string;
  data: SunburstNode;
}> = ({ title, subtitle, data }) => (
  <ChartContainer>
    <ChartHeader title={title} subtitle={subtitle} />
    <ChartBody>
      <SunburstChart data={data} size={280}>
        <SunburstBreadcrumb />
        <div className="relative flex items-center justify-center flex-1 min-h-0">
          <svg width={280} height={280} viewBox="0 0 280 280" className="transform -rotate-90">
            {(data.children || []).map((child, idx) => (
              <SunburstSegment index={idx} key={child.id} />
            ))}
          </svg>
          <SunburstCenter />
        </div>
        <SunburstHint />
      </SunburstChart>
    </ChartBody>
  </ChartContainer>
);
