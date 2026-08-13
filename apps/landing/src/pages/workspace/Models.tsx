/**
 * Workspace Page — Models Registry
 * Route: /dashboard/models
 */

import { ModelsStoreProvider } from '@/features/models/store/modelsStore';
import ModelsFeature from '@/features/models/components/ModelsFeature';

export default function WorkspaceModelsPage() {
  return (
    <ModelsStoreProvider>
      <ModelsFeature />
    </ModelsStoreProvider>
  );
}
