import type { DatasetRead } from './datasetApi';
import type { Dataset, DatasetStatus } from '../domain/types';

export function mapDatasetDtoToDomain(dto: DatasetRead): Dataset {
  let mappedStatus: DatasetStatus = 'READY';
  if (['READY', 'INDEXING', 'ERROR', 'ARCHIVED'].includes(dto.status.toUpperCase())) {
    mappedStatus = dto.status.toUpperCase() as DatasetStatus;
  }

  return {
    id: dto.id,
    name: dto.name,
    description: dto.description || '',
    type: dto.type || 'Unknown',
    samples: dto.samples || 0,
    sizeBytes: dto.size_bytes || 0,
    status: mappedStatus,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    // Safely omitting missing fields by leaving them undefined.
    thumbnailUrl: undefined,
  };
}
