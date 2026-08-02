import { BentoCard, type BentoItem } from '@/components/kokonutui/bento-grid';
import type { HeroMetric } from '@/features/datasets/domain/types';
import { AnimatedSection } from '@/components/atlas/motion';

export interface AtlasDatasetBentoProps {
  metrics: HeroMetric[];
}

export function AtlasDatasetBento({ metrics }: AtlasDatasetBentoProps) {
  // We map the pure presentation models to Kokonut's expected BentoItem interface
  const bentoItems: BentoItem[] = metrics.map((metric, index) => {
    // Map our metrics to the best Kokonut feature type
    // We determine sizing based on index to create a bento layout
    const isLarge = index === 0;
    const isWide = index === 1;

    return {
      id: metric.id,
      title: metric.title,
      description: metric.description,
      // For large/wide cards, we use 'spotlight' or standard text, for others we use 'metrics' or simple display
      feature: undefined,
      statistic: {
        label: metric.trend || metric.title,
        value: metric.value,
        end: parseInt(metric.value.replace(/[^0-9]/g, '')) || 0, // Fallback for animation
        suffix: metric.value.replace(/[0-9]/g, ''),
      },
      size: isLarge ? 'lg' : isWide ? 'md' : 'sm',
      className: isLarge 
        ? 'col-span-2 row-span-2' 
        : isWide 
          ? 'col-span-2 row-span-1' 
          : 'col-span-1 row-span-1',
    };
  });

  return (
    <AnimatedSection className="grid grid-cols-1 md:grid-cols-4 gap-4 auto-rows-[160px]">
      {bentoItems.map((item) => (
        <div key={item.id} className={item.className}>
          <BentoCard item={item} />
        </div>
      ))}
    </AnimatedSection>
  );
}
