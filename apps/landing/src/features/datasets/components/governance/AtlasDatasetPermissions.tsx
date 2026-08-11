import { useDatasetGovernance } from '../../hooks/useDatasetGovernance';
import { AtlasInsightCard } from '@/components/atlas/charts/wrappers/AtlasInsightCard';
import { AtlasAvatar } from '@/components/atlas/AtlasAvatar';
import { AtlasBadge } from '@/components/atlas/AtlasBadge';
import { AtlasTabs } from '@/components/atlas/AtlasTabs';
import type { PermissionModel } from '../../types/governance';

export function AtlasDatasetPermissions({ governance }: { governance: ReturnType<typeof useDatasetGovernance> }) {
  const { permissions } = governance;

  const PermissionList = ({ items }: { items: PermissionModel[] }) => (
    <div className="flex flex-col divide-y divide-white/5">
      {items.map(p => (
        <div key={p.id} className="flex items-center justify-between py-3 group">
          <div className="flex items-center gap-3">
            <AtlasAvatar src={p.avatarUrl} initials={p.entityName.charAt(0)} size="md" />
            <div className="flex flex-col">
              <span className="text-white text-sm">{p.entityName}</span>
              {p.lastActiveAt && (
                <span className="text-white/40 text-xs">Active {p.lastActiveAt}</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <AtlasBadge variant={p.role === 'Owner' ? 'success' : p.role === 'Admin' ? 'info' : 'outline'}>
              {p.role}
            </AtlasBadge>
            <button className="opacity-0 group-hover:opacity-100 p-1 text-white/40 hover:text-white transition-opacity">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>
            </button>
          </div>
        </div>
      ))}
      {items.length === 0 && (
        <div className="py-8 text-center text-white/40 text-sm">
          No permissions found.
        </div>
      )}
    </div>
  );

  return (
    <AtlasInsightCard title="Access & Permissions" className="h-full relative overflow-hidden pb-12">
      <AtlasTabs 
        tabs={[
          { id: 'users', label: `Users (${permissions.users.length})`, content: <PermissionList items={permissions.users} /> },
          { id: 'groups', label: `Groups (${permissions.groups.length})`, content: <PermissionList items={permissions.groups} /> },
          { id: 'service', label: `Service Accounts (${permissions.serviceAccounts.length})`, content: <PermissionList items={permissions.serviceAccounts} /> }
        ]}
      />
      <div className="absolute bottom-0 left-0 right-0 p-4 bg-neutral-900 border-t border-white/10 z-20">
        <button className="w-full py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-sm font-medium transition-colors">
          Manage Access
        </button>
      </div>
    </AtlasInsightCard>
  );
}
