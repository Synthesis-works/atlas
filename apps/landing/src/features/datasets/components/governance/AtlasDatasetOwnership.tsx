import { useDatasetGovernance } from '../../hooks/useDatasetGovernance';
import { AtlasInsightCard } from '@/components/atlas/charts/wrappers/AtlasInsightCard';
import { AtlasAvatar } from '@/components/atlas/AtlasAvatar';
import { AtlasBadge } from '@/components/atlas/AtlasBadge';
import type { UserRef } from '../../types/governance';

export function AtlasDatasetOwnership({ governance }: { governance: ReturnType<typeof useDatasetGovernance> }) {
  const { ownership } = governance;

  const OwnerRow = ({ label, user }: { label: string, user: UserRef }) => (
    <div className="flex items-center justify-between py-3 border-b border-white/5 last:border-0">
      <span className="text-white/50 text-sm">{label}</span>
      <div className="flex items-center gap-3">
        <span className="text-white text-sm">{user.name}</span>
        <AtlasAvatar src={user.avatarUrl} initials={user.name.charAt(0)} size="sm" />
      </div>
    </div>
  );

  return (
    <AtlasInsightCard title="Ownership & Responsibility" className="h-full">
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/5">
          <div className="flex flex-col gap-1">
            <span className="text-white/40 text-xs uppercase tracking-wider">Status</span>
            <span className="text-white font-medium">{ownership.status}</span>
          </div>
          <AtlasBadge variant={ownership.status === 'Active' ? 'success' : 'warning'}>
            {ownership.status}
          </AtlasBadge>
        </div>

        <div className="flex flex-col">
          <OwnerRow label="Business Owner" user={ownership.businessOwner} />
          <OwnerRow label="Technical Owner" user={ownership.technicalOwner} />
          <OwnerRow label="Steward" user={ownership.steward} />
          <OwnerRow label="Maintainer" user={ownership.maintainer} />
        </div>

        <div className="flex flex-col gap-2 mt-2 border-t border-white/10 pt-4">
          <div className="flex justify-between text-xs text-white/40">
            <span>Created by {ownership.createdBy.name}</span>
            <span>{ownership.createdAt}</span>
          </div>
          <div className="flex justify-between text-xs text-white/40">
            <span>Modified by {ownership.lastModifiedBy.name}</span>
            <span>{ownership.updatedAt}</span>
          </div>
        </div>

        <div className="flex items-center gap-2 mt-2">
          <button className="flex-1 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-white transition-colors">
            Contact
          </button>
          <button className="flex-1 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-white transition-colors">
            Transfer
          </button>
        </div>
      </div>
    </AtlasInsightCard>
  );
}
