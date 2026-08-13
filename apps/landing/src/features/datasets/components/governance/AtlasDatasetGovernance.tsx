import { useDatasetGovernance } from '../../hooks/useDatasetGovernance';
import { AtlasDatasetOwnership } from './AtlasDatasetOwnership';
import { AtlasDatasetPermissions } from './AtlasDatasetPermissions';
import { AtlasDatasetLineage } from './AtlasDatasetLineage';
import { AtlasDatasetAuditLog } from './AtlasDatasetAuditLog';
import { AtlasDatasetApprovals } from './AtlasDatasetApprovals';
import { AtlasDatasetActivity } from './AtlasDatasetActivity';
import { motion } from 'framer-motion';

export function AtlasDatasetGovernance({ datasetId }: { datasetId: string }) {
  const governance = useDatasetGovernance(datasetId);

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col gap-6"
    >
      {/* Trust Indicators (Dense Strip) */}
      <div className="flex flex-wrap gap-8 p-4 bg-white/5 border border-white/10 rounded-xl">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-white/50 uppercase tracking-wider">Approval</span>
          <span className="text-sm font-medium text-emerald-400">Approved</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-white/50 uppercase tracking-wider">Owner</span>
          <span className="text-sm font-medium text-white">Data Eng</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-white/50 uppercase tracking-wider">Permissions</span>
          <span className="text-sm font-medium text-white">Restricted</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-white/50 uppercase tracking-wider">Recent Activity</span>
          <span className="text-sm font-medium text-white">2h ago</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-white/50 uppercase tracking-wider">Audit Status</span>
          <span className="text-sm font-medium text-white">Verified</span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="flex flex-col gap-6">
          <AtlasDatasetOwnership governance={governance} />
          <AtlasDatasetApprovals governance={governance} />
          <AtlasDatasetLineage governance={governance} />
        </div>

        {/* Right Column */}
        <div className="flex flex-col gap-6">
          <AtlasDatasetPermissions governance={governance} />
          <AtlasDatasetActivity governance={governance} />
          <AtlasDatasetAuditLog governance={governance} />
        </div>
      </div>
    </motion.div>
  );
}
