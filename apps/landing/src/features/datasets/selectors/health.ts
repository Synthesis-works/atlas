import { mockDatasets } from '../domain/mock';
import type { Dataset } from '../domain/types';

export const selectAllDatasets = (): Dataset[] => {
  return mockDatasets;
};

export const selectReadyDatasets = (): Dataset[] => {
  return mockDatasets.filter(ds => ds.status === 'READY');
};

export const selectIndexingDatasets = (): Dataset[] => {
  return mockDatasets.filter(ds => ds.status === 'INDEXING');
};
