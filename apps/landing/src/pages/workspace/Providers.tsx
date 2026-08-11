import { Suspense } from 'react';
import { PageLoader } from '@/components/layout/PageLoader';
import { AtlasProviderCatalog } from '@/features/providers';

export function WorkspaceProvidersPage() {
  return (
    <Suspense fallback={<PageLoader />}>
      <div className="h-[calc(100vh-4rem)] p-4">
        <AtlasProviderCatalog />
      </div>
    </Suspense>
  );
}

export default WorkspaceProvidersPage;
