import type { Dataset, DatasetHealth, DatasetQuality } from '../domain/types';
import type { FilterState, SortState } from '../types/catalog';
import { buildDatasetCard, buildDatasetRow, buildDatasetPreview, buildDatasetComparison } from '../presentation/catalog';

// For this phase, we act purely on raw arrays provided by the caller (which may come from API or mock).
// In a real app, this might be a Redux selector or React Query selector.

export function filterDatasets(datasets: Dataset[], filters: FilterState): Dataset[] {
  return datasets.filter(ds => {
    // Search Query (Name, Description, Type)
    if (filters.searchQuery) {
      const q = filters.searchQuery.toLowerCase();
      const matchesSearch = 
        ds.name.toLowerCase().includes(q) ||
        ds.description.toLowerCase().includes(q) ||
        ds.type.toLowerCase().includes(q);
      
      if (!matchesSearch) return false;
    }

    // Status Filter
    if (filters.status.length > 0 && !filters.status.includes(ds.status)) {
      return false;
    }

    // Type Filter
    if (filters.type.length > 0 && !filters.type.includes(ds.type)) {
      return false;
    }

    // Provider, Owner, Tags (Mocking for now as they aren't on base Dataset entity)
    // If they were, we would filter them here.
    return true;
  });
}

export function sortDatasets(datasets: Dataset[], sort: SortState, healthMap: Record<string, DatasetHealth>): Dataset[] {
  return [...datasets].sort((a, b) => {
    let aVal: any = a[sort.field as keyof Dataset];
    let bVal: any = b[sort.field as keyof Dataset];

    // Handle special sort fields
    if (sort.field === 'health') {
      aVal = healthMap[a.id]?.readinessScore ?? 0;
      bVal = healthMap[b.id]?.readinessScore ?? 0;
    } else if (sort.field === 'storage') {
      aVal = a.sizeBytes;
      bVal = b.sizeBytes;
    } else if (sort.field === 'updated') {
      aVal = new Date(a.updatedAt).getTime();
      bVal = new Date(b.updatedAt).getTime();
    }

    if (aVal < bVal) return sort.direction === 'asc' ? -1 : 1;
    if (aVal > bVal) return sort.direction === 'asc' ? 1 : -1;
    return 0;
  });
}

export function selectCatalogCards(datasets: Dataset[], healthMap: Record<string, DatasetHealth>) {
  return datasets.map(ds => buildDatasetCard(ds, healthMap[ds.id]));
}

export function selectCatalogRows(datasets: Dataset[], healthMap: Record<string, DatasetHealth>) {
  return datasets.map(ds => buildDatasetRow(ds, healthMap[ds.id]));
}

export function selectDatasetPreview(dataset: Dataset, health?: DatasetHealth, quality?: DatasetQuality) {
  return buildDatasetPreview(dataset, health, quality);
}

export function selectDatasetComparison(datasets: Dataset[], healthMap: Record<string, DatasetHealth>, qualityMap: Record<string, DatasetQuality>) {
  return datasets.map(ds => buildDatasetComparison(ds, healthMap[ds.id], qualityMap[ds.id]));
}
