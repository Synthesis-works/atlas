import { cn } from '@/lib/utils';
import { LayoutTokens } from '@/design/layout';
import { AtlasDatasetHero } from '../components/hero/AtlasDatasetHero';
import { AtlasDatasetHealth } from '../components/health/AtlasDatasetHealth';
import { AtlasDatasetAnalytics } from '../components/analytics/AtlasDatasetAnalytics';
import { AtlasDatasetStorage } from '../components/storage/AtlasDatasetStorage';
import { AtlasDatasetHierarchy } from '../components/hierarchy/AtlasDatasetHierarchy';
import { getDatasetHeroMetrics } from '../selectors/hero';

import { selectStorageMetrics } from '../selectors/storage';
import { ScrambleSectionTitle } from '@/components/motion';
import { AtlasDatasetCatalog } from '../components/catalog/AtlasDatasetCatalog';

export default function DatasetsPage() {
  const storageMetrics = selectStorageMetrics();
  const mockStorageArray = [{ compressedSizeBytes: storageMetrics.totalBytes }];
  
  const heroMetrics = getDatasetHeroMetrics([], mockStorageArray as any);

  return (
    <div className="w-full py-12 flex flex-col pb-32">
      {/* SECTION 1 & 2: Page Header & Hero Summary */}
      <div className={LayoutTokens.sectionGap}>
        <AtlasDatasetHero metrics={heroMetrics} />
      </div>

      <div className={cn("flex flex-col", LayoutTokens.sectionGap)}>
        <AtlasDatasetHealth />
        <AtlasDatasetAnalytics />
        <AtlasDatasetStorage />
        <AtlasDatasetHierarchy />
      
        <div className="flex flex-col gap-6 w-full pt-section border-t border-white/5">
          <div>
            <ScrambleSectionTitle text="DATASET OPERATIONS" />
            <p className="text-white/50 text-sm">Search, manage and compare every dataset in Atlas.</p>
          </div>
          <AtlasDatasetCatalog />
        </div>
      </div>
    </div>
  );
}
