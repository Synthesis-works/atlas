export interface ProviderCardModel {
  id: string;
  name: string;
  description: string;
  status: 'operational' | 'degraded' | 'outage' | 'maintenance';
  tier: 'enterprise' | 'startup' | 'open-source';
  modelsCount: number;
  averageLatencyMs: number;
  uptimePercentage: number;
  tags: string[];
}

export interface ProviderRowModel {
  id: string;
  name: string;
  status: 'operational' | 'degraded' | 'outage' | 'maintenance';
  tier: 'enterprise' | 'startup' | 'open-source';
  modelsCount: number;
  averageLatencyMs: number;
  uptimePercentage: number;
  regions: string[];
}

export interface ProviderPreviewModel {
  id: string;
  name: string;
  description: string;
  status: 'operational' | 'degraded' | 'outage' | 'maintenance';
  tier: 'enterprise' | 'startup' | 'open-source';
  modelsCount: number;
  averageLatencyMs: number;
  uptimePercentage: number;
  regions: string[];
  supportedModalities: string[];
  apiEndpoint: string;
  compliance: string[];
  updatedAt: string;
}


export interface ProviderFilterState {
  searchQuery: string;
  status: 'all' | 'operational' | 'degraded' | 'outage' | 'maintenance';
  tier: 'all' | 'enterprise' | 'startup' | 'open-source';
}

export interface ProviderSortState {
  field: 'name' | 'modelsCount' | 'averageLatencyMs' | 'uptimePercentage';
  direction: 'asc' | 'desc';
}
