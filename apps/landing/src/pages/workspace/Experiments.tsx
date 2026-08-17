import { Suspense } from 'react';
import { PageLoader } from '@/components/layout/PageLoader';
import { EvaluationsFeature } from '@/features/evaluations';

interface Props {
  openNewModal?: boolean;
}

export function WorkspaceExperimentsPage({ openNewModal = false }: Props) {
  return (
    <Suspense fallback={<PageLoader />}>
      <div className="min-h-full p-4" data-canonical-marker="ATLAS_CANONICAL_WORKTREE_MARKER">
        <EvaluationsFeature openNewModal={openNewModal} />
      </div>
    </Suspense>
  );
}

export default WorkspaceExperimentsPage;
