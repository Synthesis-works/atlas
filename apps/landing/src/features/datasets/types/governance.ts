export interface UserRef {
  id: string;
  name: string;
  avatarUrl?: string;
  email?: string;
}

export interface OwnershipModel {
  datasetId: string;
  businessOwner: UserRef;
  technicalOwner: UserRef;
  steward: UserRef;
  maintainer: UserRef;
  createdBy: UserRef;
  lastModifiedBy: UserRef;
  createdAt: string; // Formatted date
  updatedAt: string; // Formatted date
  status: 'Active' | 'Deprecated' | 'Archived';
}

export type PermissionRole = 'Owner' | 'Admin' | 'Editor' | 'Reviewer' | 'Viewer';

export interface PermissionModel {
  id: string;
  entityId: string;
  entityName: string;
  entityType: 'User' | 'Group' | 'ServiceAccount';
  avatarUrl?: string;
  role: PermissionRole;
  status: 'Active' | 'Pending' | 'Suspended';
  lastActiveAt?: string; // Formatted date
}

export interface PermissionsStateModel {
  users: PermissionModel[];
  groups: PermissionModel[];
  serviceAccounts: PermissionModel[];
}

export interface LineageNodeModel {
  id: string;
  type: 'Source' | 'Transform' | 'Derived' | 'Model' | 'Benchmark' | 'Experiment';
  name: string;
  description?: string;
  childrenIds: string[];
}

export interface LineageModel {
  nodes: Record<string, LineageNodeModel>;
  rootId: string;
}

export interface AuditEntryModel {
  id: string;
  timestamp: string; // Formatted datetime
  user: UserRef;
  action: 'Created' | 'Updated' | 'Validated' | 'Archived' | 'Exported' | 'Permission Changed' | 'Version Created';
  beforeSnapshot?: string;
  afterSnapshot?: string;
  reason?: string;
}

export interface TimelineModel {
  id: string;
  timestamp: string; // Formatted datetime
  user: UserRef;
  action: string;
  status: 'Success' | 'Warning' | 'Failed' | 'Info';
  metadata?: Record<string, string>;
}

export type ActivityFilterDate = 'Today' | 'Week' | 'Month' | 'All';

export interface ActivityFilterModel {
  dateRange: ActivityFilterDate;
  actions: string[];
}

export interface ApprovalStep {
  id: string;
  status: 'Draft' | 'Review' | 'Approved' | 'Published' | 'Archived' | 'Rejected' | 'Changes Requested';
  approver?: UserRef;
  timestamp?: string; // Formatted datetime
  reason?: string;
  isCompleted: boolean;
  isActive: boolean;
}

export interface ApprovalModel {
  datasetId: string;
  currentStatus: string;
  steps: ApprovalStep[];
}

export interface GovernanceSummaryModel {
  datasetId: string;
  ownerName: string;
  isApproved: boolean;
  activeCollaboratorsCount: number;
}
