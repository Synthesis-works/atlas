import type { Dataset, DatasetStorage, HeroMetric } from '../domain/types';

/**
 * Selectors transform domain models into pure presentation models.
 */

// Helper to format bytes to human readable string (deterministic)
export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  // We use string manipulation to avoid floating point inconsistencies, 
  // but toFixed(1) is deterministic enough.
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

export const getDatasetHeroMetrics = (datasets: Dataset[], storage: DatasetStorage[]): HeroMetric[] => {
  const totalDatasets = datasets.length;
  const totalStorage = storage.reduce((acc, curr) => acc + curr.compressedSizeBytes, 0);
  const healthyDatasets = datasets.filter(d => d.status === 'READY').length;
  const runningPipelines = datasets.filter(d => d.status === 'INDEXING').length;
  const totalSamples = datasets.reduce((acc, curr) => acc + curr.samples, 0);

  // Format samples with K, M, B
  const formatSamples = (num: number) => {
    if (num >= 1_000_000_000) return `${(num / 1_000_000_000).toFixed(1)}B`;
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toString();
  };

  return [
    {
      id: 'total-datasets',
      title: 'Total Datasets',
      value: totalDatasets.toString(),
      trend: '+2 this month',
      trendUp: true,
      icon: 'Database', // Maps to Lucide icon in presentation
      description: 'Registered active datasets',
    },
    {
      id: 'storage-used',
      title: 'Storage Used',
      value: formatBytes(totalStorage),
      trend: '+150 GB',
      trendUp: false, // More storage isn't necessarily "good" up trend
      icon: 'HardDrive',
      description: 'Compressed storage on disk',
    },
    {
      id: 'healthy-datasets',
      title: 'Healthy Datasets',
      value: healthyDatasets.toString(),
      trend: `${Math.round((healthyDatasets / totalDatasets) * 100)}% readiness`,
      trendUp: true,
      icon: 'Activity',
      description: 'Datasets ready for benchmarks',
      status: 'success',
    },
    {
      id: 'running-pipelines',
      title: 'Running Pipelines',
      value: runningPipelines.toString(),
      icon: 'RefreshCcw',
      description: 'Active background indexing jobs',
      status: runningPipelines > 0 ? 'warning' : 'neutral',
    },
    {
      id: 'total-samples',
      title: 'Total Samples',
      value: formatSamples(totalSamples),
      icon: 'Images',
      description: 'Data points across all datasets',
    },
    {
      id: 'last-sync',
      title: 'Last Synchronization',
      value: '2 hrs ago',
      icon: 'Clock',
      description: 'Last metadata sync from providers',
    }
  ];
};
