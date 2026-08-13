import React from 'react';
import { SunburstChart } from '@/components/charts/sunburst-chart';
import { SunburstBreadcrumb, useSunburstBreadcrumbItems } from '@/components/charts/sunburst-breadcrumb';
import { SunburstSegment } from '@/components/charts/sunburst-segment';
import { SunburstCenter } from '@/components/charts/sunburst-center';
import { SunburstLabels } from '@/components/charts/sunburst-labels';
import { SunburstHint } from '@/components/charts/sunburst-hint';
import { buildArcs } from '@/components/charts/sunburst';
import { ChevronRight } from 'lucide-react';

const DrillBreadcrumb = () => {
  const { items, zoomTo } = useSunburstBreadcrumbItems();
  return (
    <div className="flex items-center gap-1 text-xs text-white/50 bg-black/40 px-3 py-1.5 rounded-full backdrop-blur-md w-max border border-white/10">
      {items.map((item, i) => (
        <React.Fragment key={item.id}>
          {i > 0 && <ChevronRight className="w-3 h-3 text-white/30" />}
          <span 
            className={`cursor-pointer hover:text-white transition-colors ${item.isCurrent ? 'text-white' : ''}`}
            onClick={() => zoomTo(item.id)}
          >
            {item.label}
          </span>
        </React.Fragment>
      ))}
    </div>
  );
};

export interface AtlasSunburstChartProps {
  tree: any;
  title?: string;
  description?: string;
}

export const AtlasSunburstChart: React.FC<AtlasSunburstChartProps> = ({ tree }) => {
  const { arcs } = buildArcs(tree);

  return (
    <div className="w-full flex justify-center items-center min-h-[440px]">
      <SunburstChart data={tree} size={440}>
        <SunburstBreadcrumb>
          <DrillBreadcrumb />
        </SunburstBreadcrumb>
        {arcs.map((arc: any) => (
          <SunburstSegment index={arc.arcIndex} key={arc.id} />
        ))}
        <SunburstCenter />
        <SunburstLabels />
        <SunburstHint />
      </SunburstChart>
    </div>
  );
};
