import { useState, useMemo } from 'react';
import type { ActivityFilterModel } from '../types/governance';
import { 
  selectOwnership, 
  selectPermissions, 
  selectLineage, 
  selectAuditLogs, 
  selectActivityTimeline, 
  selectApprovals,
  selectMockComments
} from '../selectors/governance';

export function useDatasetGovernance(datasetId: string) {
  // Lineage State
  const [expandedNodes, setExpandedNodes] = useState<string[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const handleNodeExpand = (nodeId: string) => {
    setExpandedNodes(prev => prev.includes(nodeId) ? prev.filter(id => id !== nodeId) : [...prev, nodeId]);
  };

  const handleNodeSelect = (nodeId: string) => {
    setSelectedNodeId(nodeId === selectedNodeId ? null : nodeId);
  };

  // Audit Log State
  const [auditSearch, setAuditSearch] = useState('');
  const [auditActionFilter, setAuditActionFilter] = useState('');

  // Activity Timeline State
  const [activityFilter, setActivityFilter] = useState<ActivityFilterModel>({
    dateRange: 'All',
    actions: []
  });

  // Approvals State
  const [selectedApproverId, setSelectedApproverId] = useState<string | null>(null);

  // Data fetching (via selectors, memoized for now)
  const ownership = useMemo(() => selectOwnership(datasetId), [datasetId]);
  const permissions = useMemo(() => selectPermissions(datasetId), [datasetId]);
  const lineage = useMemo(() => selectLineage(datasetId), [datasetId]);
  const auditLogs = useMemo(() => selectAuditLogs(datasetId, { search: auditSearch, action: auditActionFilter }), [datasetId, auditSearch, auditActionFilter]);
  const activityTimeline = useMemo(() => selectActivityTimeline(datasetId, activityFilter), [datasetId, activityFilter]);
  const approvals = useMemo(() => selectApprovals(datasetId), [datasetId]);
  const collaborationComments = useMemo(() => selectMockComments(datasetId), [datasetId]);

  return {
    // State
    lineageState: {
      expandedNodes,
      selectedNodeId
    },
    auditState: {
      search: auditSearch,
      actionFilter: auditActionFilter
    },
    activityFilter,
    selectedApproverId,

    // Actions
    handleNodeExpand,
    handleNodeSelect,
    setAuditSearch,
    setAuditActionFilter,
    setActivityFilter,
    setSelectedApproverId,

    // Derived Data Models
    ownership,
    permissions,
    lineage,
    auditLogs,
    activityTimeline,
    approvals,
    collaborationComments
  };
}
