// We mock the domain entities (for this mock file we'll just mock the presentation-ready structures 
// to avoid over-engineering the mock domain layer, but in reality these would be raw DTOs).
// Given the instruction "No domain objects reach the UI. Replacing mock data with REST... must require changes only to selectors and presentation models."
// We will mock raw-ish data and let presentation layer format it.

export const mockUsers = {
  alex: { id: 'u1', name: 'Alex Chen', email: 'alex@atlas.com', avatarUrl: 'https://i.pravatar.cc/150?u=a042581f4e29026024d' },
  sarah: { id: 'u2', name: 'Sarah Miller', email: 'sarah@atlas.com', avatarUrl: 'https://i.pravatar.cc/150?u=a04258a2462d826712d' },
  marcus: { id: 'u3', name: 'Marcus Johnson', email: 'marcus@atlas.com', avatarUrl: 'https://i.pravatar.cc/150?u=a042581f4e29026704d' },
  system: { id: 'sys1', name: 'Atlas System', email: 'system@atlas.com', avatarUrl: 'https://i.pravatar.cc/150?u=sys' },
};

export const rawMockOwnership = {
  datasetId: 'mock-dataset-1',
  businessOwnerId: 'u2',
  technicalOwnerId: 'u1',
  stewardId: 'u3',
  maintainerId: 'u1',
  createdById: 'u2',
  lastModifiedById: 'u1',
  createdAt: '2023-11-10T14:00:00Z',
  updatedAt: '2023-12-01T09:30:00Z',
  status: 'Active' as const,
};

export const rawMockPermissions = [
  { id: 'p1', entityId: 'u1', entityName: 'Alex Chen', entityType: 'User', role: 'Owner', status: 'Active', lastActiveAt: '2023-12-01T08:00:00Z' },
  { id: 'p2', entityId: 'g1', entityName: 'Data Science Team', entityType: 'Group', role: 'Editor', status: 'Active', lastActiveAt: '2023-11-28T10:00:00Z' },
  { id: 'p3', entityId: 'sa1', entityName: 'ETL Pipeline', entityType: 'ServiceAccount', role: 'Viewer', status: 'Active', lastActiveAt: '2023-12-01T09:00:00Z' },
];

export const rawMockLineageNodes = [
  { id: 'l1', type: 'Source', name: 'Raw User Events', childrenIds: ['l2'] },
  { id: 'l2', type: 'Transform', name: 'Cleanse & Anonymize', childrenIds: ['l3'] },
  { id: 'l3', type: 'Derived', name: 'Clean User Events (This Dataset)', childrenIds: ['l4', 'l5'] },
  { id: 'l4', type: 'Model', name: 'Churn Predictor v2', childrenIds: [] },
  { id: 'l5', type: 'Benchmark', name: 'Privacy Compliance Scan', childrenIds: [] },
];

export const rawMockAuditLogs = [
  { id: 'a1', timestamp: '2023-12-01T09:30:00Z', userId: 'u1', action: 'Updated', reason: 'Added new feature columns' },
  { id: 'a2', timestamp: '2023-11-25T14:15:00Z', userId: 'u2', action: 'Permission Changed', reason: 'Granted ETL pipeline access' },
  { id: 'a3', timestamp: '2023-11-10T14:00:00Z', userId: 'u2', action: 'Created', reason: 'Initial ingestion' },
];

export const rawMockActivity = [
  { id: 'act1', timestamp: '2023-12-01T10:00:00Z', userId: 'u1', action: 'Triggered Dataset Validation', status: 'Success' },
  { id: 'act2', timestamp: '2023-11-30T15:30:00Z', userId: 'u3', action: 'Requested Approval', status: 'Info' },
  { id: 'act3', timestamp: '2023-11-29T08:45:00Z', userId: 'sys1', action: 'Automated Data Quality Check', status: 'Warning', metadata: { issues: '2 schema mismatches' } },
];

export const rawMockApprovals = [
  { id: 'app1', status: 'Draft', isCompleted: true, isActive: false },
  { id: 'app2', status: 'Review', approverId: 'u3', timestamp: '2023-11-30T15:30:00Z', isCompleted: true, isActive: false, reason: 'Looks good' },
  { id: 'app3', status: 'Approved', approverId: 'u2', timestamp: '2023-12-01T09:00:00Z', isCompleted: true, isActive: true, reason: 'Approved for production' },
  { id: 'app4', status: 'Published', isCompleted: false, isActive: false },
];

export const mockComments = [
  { id: 'c1', userId: 'u1', content: 'Need validation on new annotations.', timestamp: 'Yesterday' },
  { id: 'c2', userId: 'u2', content: 'Benchmark complete. Results look promising.', timestamp: '2 days ago' },
];
