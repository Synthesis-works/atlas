import type { MockExperimentEntity } from '../mocks/mock';
import type {
  ExperimentRowModel,
  ExperimentPreviewModel,
  ExperimentFilterState,
  ExperimentSortState
} from '../types/catalog';

function formatDuration(ms: number | undefined): string {
  if (!ms) return '--';
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}m ${s}s`;
}

export function buildExperimentRowModel(entity: MockExperimentEntity): ExperimentRowModel {
  const currentStage = entity.stages[entity.currentStageIndex];
  const stageName = currentStage ? currentStage.name : 'Unknown Stage';
  const stageCountText = `Stage ${entity.currentStageIndex + 1} of ${entity.totalStages}`;
  const etaText = entity.etaMs ? `ETA ${formatDuration(entity.etaMs)}` : '';
  const durationText = formatDuration(entity.durationMs);

  return {
    id: entity.id,
    name: entity.name,
    status: entity.status,
    progressPercentage: entity.progressPercentage,
    currentStage: stageName,
    stageCountText,
    etaText,
    durationText,
    queuedAt: entity.queuedAt,
    tags: entity.tags
  };
}

export function buildExperimentPreviewModel(entity: MockExperimentEntity): ExperimentPreviewModel {
  return {
    id: entity.id,
    name: entity.name,
    status: entity.status,
    owner: entity.owner,
    startedAt: entity.startedAt || null,
    durationText: formatDuration(entity.durationMs),
    timeline: [],
    logs: entity.logs,
    metrics: entity.metrics,
    config: entity.config
  };
}

export function selectExperimentCatalog(
  rawEntities: MockExperimentEntity[],
  filters: ExperimentFilterState,
  sort: ExperimentSortState,
  page: number,
  pageSize: number
) {
  // Filter
  const filtered = rawEntities.filter(exp => {
    if (filters.status !== 'all' && exp.status !== filters.status) return false;
    if (filters.searchQuery) {
      const q = filters.searchQuery.toLowerCase();
      if (!exp.name.toLowerCase().includes(q) && !exp.owner.toLowerCase().includes(q)) {
        return false;
      }
    }
    return true;
  });

  // Sort
  const sorted = [...filtered].sort((a, b) => {
    let comparison = 0;
    switch (sort.field) {
      case 'name':
        comparison = a.name.localeCompare(b.name);
        break;
      case 'progress':
        comparison = a.progressPercentage - b.progressPercentage;
        break;
      case 'queuedAt':
        comparison = new Date(a.queuedAt).getTime() - new Date(b.queuedAt).getTime();
        break;
    }
    return sort.direction === 'asc' ? comparison : -comparison;
  });

  // Paginate
  const totalItems = sorted.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const offset = (page - 1) * pageSize;
  const paginated = sorted.slice(offset, offset + pageSize);

  return {
    rows: paginated.map(buildExperimentRowModel),
    rawVisibleIds: paginated.map(p => p.id),
    pagination: {
      currentPage: page,
      totalPages,
      totalItems,
      pageSize,
      hasNextPage: page < totalPages,
      hasPrevPage: page > 1
    }
  };
}

export function selectExperimentPreview(entity: MockExperimentEntity | null): ExperimentPreviewModel | null {
  if (!entity) return null;
  return buildExperimentPreviewModel(entity);
}
