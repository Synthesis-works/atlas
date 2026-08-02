import type { RegistryModel, ModelHealth, ModelCost } from '../../../domain/models/types';
import type { FilterState, SortState } from '../types/catalog';
import { buildModelCard, buildModelRow, buildModelPreview, buildModelComparison } from '../presentation/catalog';

export function filterModels(models: RegistryModel[], filters: FilterState): RegistryModel[] {
  return models.filter(model => {
    // Search Query (Name, Description, Provider)
    if (filters.searchQuery) {
      const q = filters.searchQuery.toLowerCase();
      const matchesSearch = 
        model.name.toLowerCase().includes(q) ||
        model.description.toLowerCase().includes(q) ||
        model.provider.toLowerCase().includes(q);
      
      if (!matchesSearch) return false;
    }

    // Status Filter
    if (filters.status.length > 0 && !filters.status.includes(model.status)) {
      return false;
    }

    // Provider Filter
    if (filters.provider.length > 0 && !filters.provider.includes(model.provider)) {
      return false;
    }

    // Modalities Filter
    if (filters.modalities.length > 0) {
      const hasModality = filters.modalities.some(m => model.modalities.includes(m as any));
      if (!hasModality) return false;
    }

    // Capabilities Filter
    if (filters.capabilities.length > 0) {
      const hasCapability = filters.capabilities.some(c => model.capabilityTags.includes(c as any));
      if (!hasCapability) return false;
    }

    // License Filter
    if (filters.license.length > 0 && !filters.license.includes(model.license)) {
      return false;
    }

    return true;
  });
}

export function sortModels(models: RegistryModel[], sort: SortState, healthMap: Record<string, ModelHealth>): RegistryModel[] {
  return [...models].sort((a, b) => {
    let aVal: any = a[sort.field as keyof RegistryModel];
    let bVal: any = b[sort.field as keyof RegistryModel];

    // Handle special sort fields
    if (sort.field === 'score') {
      aVal = a.overallScore;
      bVal = b.overallScore;
    } else if (sort.field === 'latency') {
      aVal = a.latencyMs;
      bVal = b.latencyMs;
    } else if (sort.field === 'context') {
      aVal = a.contextWindow;
      bVal = b.contextWindow;
    } else if (sort.field === 'updated') {
      aVal = new Date(a.lastEvaluated).getTime();
      bVal = new Date(b.lastEvaluated).getTime();
    } else if (sort.field === 'name') {
      aVal = a.name.toLowerCase();
      bVal = b.name.toLowerCase();
    }

    if (aVal < bVal) return sort.direction === 'asc' ? -1 : 1;
    if (aVal > bVal) return sort.direction === 'asc' ? 1 : -1;
    return 0;
  });
}

export function selectCatalogCards(models: RegistryModel[], healthMap: Record<string, ModelHealth>) {
  return models.map(model => buildModelCard(model, healthMap[model.id]));
}

export function selectCatalogRows(models: RegistryModel[], healthMap: Record<string, ModelHealth>) {
  return models.map(model => buildModelRow(model, healthMap[model.id]));
}

export function selectModelPreview(model: RegistryModel, health?: ModelHealth, cost?: ModelCost) {
  return buildModelPreview(model, health, cost);
}

export function selectModelComparison(models: RegistryModel[], healthMap: Record<string, ModelHealth>, costMap: Record<string, ModelCost>) {
  return models.map(model => buildModelComparison(model, healthMap[model.id], costMap[model.id]));
}
