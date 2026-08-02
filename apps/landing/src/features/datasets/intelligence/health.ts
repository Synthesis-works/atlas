import { selectAllDatasets, selectReadyDatasets, selectIndexingDatasets } from '../selectors/health';
import type { AtlasInsight } from '@/domain/intelligence/types';

export const computeDatasetReadinessInsight = (): AtlasInsight => {
  const all = selectAllDatasets();
  const ready = selectReadyDatasets();
  const indexing = selectIndexingDatasets();
  
  const score = all.length > 0 ? (ready.length / all.length) * 100 : 0;
  
  return {
    id: 'health_readiness',
    title: 'Dataset Readiness',
    description: 'Overall availability and validation status of configured datasets.',
    priority: score >= 90 ? 'healthy' : score >= 70 ? 'warning' : 'critical',
    confidence: 98,
    source: 'computed',
    primaryKpi: {
      value: `${score.toFixed(0)}%`,
      label: 'Overall Readiness',
      trend: '↑ 4%'
    },
    secondaryKpi: {
      value: ready.length.toString(),
      label: 'Validated Datasets'
    },
    insight: 'Metadata completeness improved 6%. 12 datasets require manual review.',
    recommendations: [
      { priority: 1, text: `Run duplicate detection on ${indexing.length} indexing datasets` },
      { priority: 2, text: 'Validate annotations for KITTI' }
    ],
    metadata: [
      { label: 'Observation Period', value: 'Last 30 Days' },
      { label: 'Last Updated', value: 'Just now' }
    ]
  };
};

export const computeAnnotationCoverageInsight = (): AtlasInsight => {
  return {
    id: 'health_coverage',
    title: 'Annotation Coverage',
    description: 'Distribution of annotation completeness across the fleet.',
    priority: 'info',
    confidence: 95,
    source: 'ai',
    primaryKpi: {
      value: '84%',
      label: 'Fully Annotated'
    },
    secondaryKpi: {
      value: '3,212',
      label: 'Pending'
    },
    insight: 'NLP datasets are lagging in entity coverage compared to Vision tasks.',
    recommendations: [
      { priority: 1, text: 'Allocate labelers to WMT14' }
    ],
    metadata: [
      { label: 'Data Source', value: 'Annotation API' },
      { label: 'Refresh Rate', value: 'Live' }
    ],
    legend: [
      { color: '#10b981', label: 'Annotated', value: '24,120', percentage: '84%' },
      { color: '#f59e0b', label: 'Pending', value: '3,212', percentage: '12%' },
      { color: '#f43f5e', label: 'Missing', value: '821', percentage: '4%' }
    ]
  };
};
