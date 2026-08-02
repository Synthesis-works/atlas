import { Suspense } from 'react';
import { PageLoader } from '@/components/layout/PageLoader';
import { AtlasExperimentCatalog } from '@/features/experiments';

export function WorkspaceExperimentsPage() {
  return (
    <Suspense fallback={<PageLoader />}>
      <div className="h-[calc(100vh-4rem)] p-4">
        <AtlasExperimentCatalog />
      </div>
    </Suspense>
  );
}

export default WorkspaceExperimentsPage;
