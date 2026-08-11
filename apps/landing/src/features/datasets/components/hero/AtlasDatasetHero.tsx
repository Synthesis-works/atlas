import { ScrambleHeading } from '@/components/motion';
import { AnimatedSection } from '@/components/atlas/motion';
import { Button } from '@/components/ui/button';
import { Plus, Download, BookOpen } from 'lucide-react';
import { AtlasDatasetBento } from '@/components/atlas/cards/AtlasDatasetBento';
import type { HeroMetric } from '@/features/datasets/domain/types';

export interface AtlasDatasetHeroProps {
  metrics: HeroMetric[];
}

export function AtlasDatasetHero({ metrics }: AtlasDatasetHeroProps) {
  return (
    <div className="flex flex-col gap-8 mb-12">
      <AnimatedSection className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <ScrambleHeading text="DATASETS" delay={0} />
          <p className="text-white/60 text-lg max-w-2xl mt-4">
            Manage, explore and understand every dataset powering Atlas.
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Button variant="outline" className="bg-white/5 border-white/10 hover:bg-white/10">
            <BookOpen className="w-4 h-4 mr-2" />
            Documentation
          </Button>
          <Button variant="outline" className="bg-white/5 border-white/10 hover:bg-white/10">
            <Download className="w-4 h-4 mr-2" />
            Import Dataset
          </Button>
          <Button className="bg-accent text-white hover:bg-accent-hover">
            <Plus className="w-4 h-4 mr-2" />
            Create Dataset
          </Button>
        </div>
      </AnimatedSection>

      <AtlasDatasetBento metrics={metrics} />
    </div>
  );
}
