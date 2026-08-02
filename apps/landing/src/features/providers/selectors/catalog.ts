import type { MockProviderEntity } from '../mocks/mock';
import type {
  ProviderCardModel,
  ProviderRowModel,
  ProviderPreviewModel,
  ProviderFilterState,
  ProviderSortState
} from '../types/catalog';

function sortProviders(providers: MockProviderEntity[], sort: ProviderSortState): MockProviderEntity[] {
  return [...providers].sort((a, b) => {
    let comparison = 0;
    switch (sort.field) {
      case 'name':
        comparison = a.name.localeCompare(b.name);
        break;
      case 'modelsCount':
        comparison = a.modelsCount - b.modelsCount;
        break;
      case 'averageLatencyMs':
        comparison = a.averageLatencyMs - b.averageLatencyMs;
        break;
      case 'uptimePercentage':
        comparison = a.uptimePercentage - b.uptimePercentage;
        break;
    }
    return sort.direction === 'asc' ? comparison : -comparison;
  });
}

function filterProviders(providers: MockProviderEntity[], filters: ProviderFilterState): MockProviderEntity[] {
  return providers.filter(provider => {
    if (filters.status !== 'all' && provider.status !== filters.status) return false;
    if (filters.tier !== 'all' && provider.tier !== filters.tier) return false;
    if (filters.searchQuery) {
      const q = filters.searchQuery.toLowerCase();
      if (!provider.name.toLowerCase().includes(q) && !provider.description.toLowerCase().includes(q)) {
        return false;
      }
    }
    return true;
  });
}

export function buildProviderCardModel(entity: MockProviderEntity): ProviderCardModel {
  return {
    id: entity.id,
    name: entity.name,
    description: entity.description,
    status: entity.status,
    tier: entity.tier,
    modelsCount: entity.modelsCount,
    averageLatencyMs: entity.averageLatencyMs,
    uptimePercentage: entity.uptimePercentage,
    tags: entity.supportedModalities.slice(0, 3)
  };
}

export function buildProviderRowModel(entity: MockProviderEntity): ProviderRowModel {
  return {
    id: entity.id,
    name: entity.name,
    status: entity.status,
    tier: entity.tier,
    modelsCount: entity.modelsCount,
    averageLatencyMs: entity.averageLatencyMs,
    uptimePercentage: entity.uptimePercentage,
    regions: entity.regions
  };
}

export function buildProviderPreviewModel(entity: MockProviderEntity): ProviderPreviewModel {
  return {
    id: entity.id,
    name: entity.name,
    description: entity.description,
    status: entity.status,
    tier: entity.tier,
    modelsCount: entity.modelsCount,
    averageLatencyMs: entity.averageLatencyMs,
    uptimePercentage: entity.uptimePercentage,
    regions: entity.regions,
    supportedModalities: entity.supportedModalities,
    apiEndpoint: entity.apiEndpoint,
    compliance: entity.compliance,
    updatedAt: entity.updatedAt
  };
}

export function selectProviderCatalog(
  rawEntities: MockProviderEntity[],
  filters: ProviderFilterState,
  sort: ProviderSortState,
  page: number,
  pageSize: number
) {
  const filtered = filterProviders(rawEntities, filters);
  const sorted = sortProviders(filtered, sort);
  
  const totalItems = sorted.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const offset = (page - 1) * pageSize;
  const paginated = sorted.slice(offset, offset + pageSize);

  return {
    cards: paginated.map(buildProviderCardModel),
    rows: paginated.map(buildProviderRowModel),
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

export function selectProviderPreview(entity: MockProviderEntity | null): ProviderPreviewModel | null {
  if (!entity) return null;
  return buildProviderPreviewModel(entity);
}
