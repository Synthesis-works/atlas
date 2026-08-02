import type { RegistryModel } from '@/domain/models/types';
import { AtlasRadarChart } from '@/components/atlas/charts';
import type { RadarSeries } from '@/components/atlas/charts';

interface Props {
  model: RegistryModel;
  size?: number;
  showLabels?: boolean;
}

const AXES = ['Coding', 'Reasoning', 'Math', 'Knowledge', 'Vision', 'Safety', 'Tool Use', 'Speed'];

export function CapabilityRadar({ model, size = 320, showLabels = true }: Props) {
  const values: Record<string, number> = {};
  AXES.forEach((ax) => {
    const cap = model.profile.capabilities.find((c) => c.domain === ax);
    values[ax] = cap ? cap.score : 0;
  });

  const radarData: RadarSeries[] = [
    {
      label: model.name,
      values,
    },
  ];

  return (
    <div className="flex justify-center p-8">
      <AtlasRadarChart
      data={radarData}
      size={size}
      showAxisLabels={showLabels}
      showGridLabels={false}
      showPoints={false}
    />
    </div>
  );
}
