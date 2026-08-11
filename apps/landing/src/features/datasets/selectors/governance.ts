import { 
  rawMockOwnership, 
  rawMockPermissions, 
  rawMockLineageNodes, 
  rawMockAuditLogs, 
  rawMockActivity, 
  rawMockApprovals,
  mockUsers,
  mockComments
} from '../domain/mock/governance';
import { 
  buildOwnershipModel, 
  buildPermissionsModel, 
  buildLineageModel, 
  buildAuditLogModel, 
  buildActivityTimelineModel, 
  buildApprovalModel 
} from '../presentation/governance';
import type { ActivityFilterModel } from '../types/governance';

// Helper to resolve user
const resolveUser = (id: string) => {
  const u = (mockUsers as any)[Object.keys(mockUsers).find(k => (mockUsers as any)[k].id === id) || 'system'];
  return u || { id, name: 'Unknown User' };
};

export function selectOwnership(_datasetId: string) {
  // In real life, fetch by datasetId
  return buildOwnershipModel(rawMockOwnership, resolveUser);
}

export function selectPermissions(_datasetId: string) {
  return buildPermissionsModel(rawMockPermissions);
}

export function selectLineage(_datasetId: string) {
  return buildLineageModel(rawMockLineageNodes, 'l3'); // l3 is the current dataset in mock
}

export function selectAuditLogs(_datasetId: string, filters?: { search?: string, action?: string }) {
  let logs = rawMockAuditLogs;
  
  if (filters?.search) {
    const q = filters.search.toLowerCase();
    logs = logs.filter(l => 
      l.action.toLowerCase().includes(q) || 
      (l.reason && l.reason.toLowerCase().includes(q))
    );
  }
  
  if (filters?.action) {
    logs = logs.filter(l => l.action === filters.action);
  }
  
  return buildAuditLogModel(logs, resolveUser);
}

export function selectActivityTimeline(_datasetId: string, filter: ActivityFilterModel) {
  let activities = rawMockActivity;
  
  // Date filtering logic (simplified mock)
  if (filter.dateRange === 'Today') {
    // mock logic
  }
  
  return buildActivityTimelineModel(activities, resolveUser);
}

export function selectApprovals(datasetId: string) {
  return buildApprovalModel(datasetId, rawMockApprovals, resolveUser);
}

export function selectMockComments(_datasetId: string) {
  return mockComments.map(c => ({
    ...c,
    user: resolveUser(c.userId)
  }));
}
