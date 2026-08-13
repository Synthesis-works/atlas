import type { 
  OwnershipModel, 
  PermissionModel, 
  PermissionsStateModel,
  LineageNodeModel,
  LineageModel,
  AuditEntryModel,
  TimelineModel,
  ApprovalStep,
  ApprovalModel,
  UserRef
} from '../types/governance';

// Formatters
const formatDate = (iso: string) => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
const formatDateTime = (iso: string) => new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });

// We pass in a resolveUser function to simulate fetching relations
export function buildOwnershipModel(raw: any, resolveUser: (id: string) => UserRef): OwnershipModel {
  return {
    datasetId: raw.datasetId,
    businessOwner: resolveUser(raw.businessOwnerId),
    technicalOwner: resolveUser(raw.technicalOwnerId),
    steward: resolveUser(raw.stewardId),
    maintainer: resolveUser(raw.maintainerId),
    createdBy: resolveUser(raw.createdById),
    lastModifiedBy: resolveUser(raw.lastModifiedById),
    createdAt: formatDate(raw.createdAt),
    updatedAt: formatDate(raw.updatedAt),
    status: raw.status
  };
}

export function buildPermissionsModel(rawList: any[]): PermissionsStateModel {
  const users: PermissionModel[] = [];
  const groups: PermissionModel[] = [];
  const serviceAccounts: PermissionModel[] = [];

  rawList.forEach(raw => {
    const model: PermissionModel = {
      id: raw.id,
      entityId: raw.entityId,
      entityName: raw.entityName,
      entityType: raw.entityType as any,
      role: raw.role as any,
      status: raw.status as any,
      lastActiveAt: raw.lastActiveAt ? formatDate(raw.lastActiveAt) : undefined,
      avatarUrl: raw.entityType === 'User' ? `https://i.pravatar.cc/150?u=${raw.entityId}` : undefined
    };
    if (model.entityType === 'User') users.push(model);
    else if (model.entityType === 'Group') groups.push(model);
    else serviceAccounts.push(model);
  });

  return { users, groups, serviceAccounts };
}

export function buildLineageModel(rawNodes: any[], rootId: string): LineageModel {
  const nodes: Record<string, LineageNodeModel> = {};
  rawNodes.forEach(n => {
    nodes[n.id] = { ...n };
  });
  return { nodes, rootId };
}

export function buildAuditLogModel(rawList: any[], resolveUser: (id: string) => UserRef): AuditEntryModel[] {
  return rawList.map(raw => ({
    id: raw.id,
    timestamp: formatDateTime(raw.timestamp),
    user: resolveUser(raw.userId),
    action: raw.action,
    reason: raw.reason,
    beforeSnapshot: raw.beforeSnapshot,
    afterSnapshot: raw.afterSnapshot
  }));
}

export function buildActivityTimelineModel(rawList: any[], resolveUser: (id: string) => UserRef): TimelineModel[] {
  return rawList.map(raw => ({
    id: raw.id,
    timestamp: formatDateTime(raw.timestamp),
    user: resolveUser(raw.userId),
    action: raw.action,
    status: raw.status,
    metadata: raw.metadata
  }));
}

export function buildApprovalModel(datasetId: string, rawSteps: any[], resolveUser: (id: string) => UserRef): ApprovalModel {
  const steps: ApprovalStep[] = rawSteps.map(raw => ({
    id: raw.id,
    status: raw.status,
    approver: raw.approverId ? resolveUser(raw.approverId) : undefined,
    timestamp: raw.timestamp ? formatDateTime(raw.timestamp) : undefined,
    reason: raw.reason,
    isCompleted: raw.isCompleted,
    isActive: raw.isActive
  }));

  const activeStep = steps.find(s => s.isActive) || steps[steps.length - 1];

  return {
    datasetId,
    currentStatus: activeStep.status,
    steps
  };
}
