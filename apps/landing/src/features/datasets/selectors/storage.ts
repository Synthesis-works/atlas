import { selectAllDatasets } from '../selectors/health';

export const selectStorageMetrics = () => {
  const datasets = selectAllDatasets();
  const totalBytes = datasets.reduce((sum, ds) => sum + ds.sizeBytes, 0);
  
  return {
    totalBytes,
    totalTb: totalBytes / (1024 * 1024 * 1024 * 1024)
  };
};
