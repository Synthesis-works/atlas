/**
 * CapabilitySnapshot — embedded radar of the top model capability profile
 */

import { Card, Badge } from '@/design/primitives';
import { ScrambleSectionTitle } from '@/components/motion';
import { AtlasRadarChart } from '@/components/atlas/charts';
import type { RadarSeries } from '@/components/atlas/charts';

export interface CapabilityDataProps {
  model_name?: string;
  provider?: string;
  rank?: number;
  score?: number;
  capabilities?: Array<{ domain: string; score: number }>;
}

function MiniRadar({ scores, name }: { scores: { domain: string; score: number }[], name: string }) {
  const radarData: RadarSeries[] = [
    {
      label: name,
      values: scores.reduce((acc, curr) => ({ ...acc, [curr.domain]: curr.score }), {}),
    }
  ];

  return (
    <div className="p-6 border border-white/5 bg-white/[0.02] rounded-2xl flex flex-col gap-6 h-full shadow-2xl shadow-black/50 relative overflow-hidden">
      <h3 className="text-sm uppercase tracking-widest text-white/40 font-medium">Model Capability Profile</h3>
      
      <div className="flex-1 flex items-center justify-center">
        <AtlasRadarChart 
          data={radarData}
          size={320}
          levels={3}
          showAxisLabels={true}
          className="mx-auto"
        />
      </div>
    </div>
  );
}

export function CapabilitySnapshot({
  capability = {
    model_name: 'Gemini 1.5 Pro',
    provider: 'Google AI',
    capabilities: [
      { domain: 'Coding', score: 84.5 },
      { domain: 'Reasoning', score: 88.0 },
      { domain: 'Math', score: 81.2 },
      { domain: 'Safety', score: 92.4 },
      { domain: 'Instruction', score: 89.0 },
    ],
  },
}: {
  capability?: CapabilityDataProps;
}) {
  const modelName = capability.model_name || 'Gemini 1.5 Pro';
  const provider = capability.provider || 'Google AI';
  const caps = capability.capabilities || [];

  return (
    <section className="liquid-glass-card rounded-2xl p-5 border border-white/10 w-full flex flex-col min-h-0 shrink-0">
      <ScrambleSectionTitle text="Capability Radar" className="text-xs tracking-[0.2em] uppercase text-white/20 mb-4" />

      <Card className="!p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-sm font-semibold text-white">{modelName}</p>
            <p className="text-xs text-white/25">{provider}</p>
          </div>
          <Badge variant="accent">Top Rank #1</Badge>
        </div>

        <MiniRadar scores={caps} name={modelName} />

        <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-1">
          {caps.map((cap) => (
            <div key={cap.domain} className="flex justify-between text-xs">
              <span className="text-white/25">{cap.domain}</span>
              <span className="text-white/50 tabular-nums">{cap.score.toFixed(1)}</span>
            </div>
          ))}
        </div>
      </Card>
    </section>
  );
}
