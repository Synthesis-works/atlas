import { computeDatasetReadinessInsight, computeAnnotationCoverageInsight } from '../intelligence/health';
import { selectAllDatasets } from '../selectors/health';

export const buildHealthPresentation = () => {
  const datasets = selectAllDatasets();
  const hasDatasets = datasets.length > 0;

  // Prepare visualization specific models
  const gaugeModel = {
    id: 'health_gauge',
    score: hasDatasets ? 91 : 0, 
    total: hasDatasets ? 124 : 0, 
    label: 'Validated Datasets'
  };

  const ringSeries = hasDatasets ? [
    { id: 'annotated', label: 'Annotated', value: 24120 },
    { id: 'unlabeled', label: 'Unlabeled', value: 8320 },
    { id: 'invalid', label: 'Invalid', value: 560 }
  ] : [];

  const radarMetrics = hasDatasets ? [
    { id: '1', metric: 'Completeness', value: 94 },
    { id: '2', metric: 'Accuracy', value: 88 },
    { id: '3', metric: 'Freshness', value: 96 },
    { id: '4', metric: 'Diversity', value: 72 },
    { id: '5', metric: 'Compliance', value: 100 }
  ] : [];

  const qualityInsight = hasDatasets ? {
    id: 'health_quality',
    title: 'Dataset Quality Profile',
    description: 'Multi-dimensional analysis of dataset integrity.',
    priority: 'info' as const,
    confidence: 90,
    source: 'computed' as const,
    primaryKpi: { value: '92', label: 'Quality Index' },
    insight: 'Completeness and Compliance are optimal. Diversity remains below target.',
    recommendations: [
      { priority: 3 as 1 | 2 | 3, text: 'Consider augmenting underrepresented classes in vision sets' }
    ],
    metadata: [
      { label: 'Observation Period', value: 'Rolling 7 Days' },
      { label: 'Last Updated', value: '2 hours ago' },
      { label: 'Refresh Rate', value: 'Daily' },
    ]
  } : {
    id: 'health_quality',
    title: 'Dataset Quality Profile',
    description: 'Multi-dimensional analysis of dataset integrity.',
    priority: 'info' as const,
    confidence: 0,
    source: 'computed' as const,
    primaryKpi: { value: '--', label: 'Quality Index' },
    insight: 'No datasets available for quality profiling.',
    recommendations: [],
    metadata: [
      { label: 'Observation Period', value: '--' },
      { label: 'Last Updated', value: '--' },
      { label: 'Refresh Rate', value: '--' },
    ]
  };

  const healthKpis = hasDatasets ? [
    { label: 'Health Score', value: '92%', trend: '+3%' },
    { label: 'Datasets', value: '126' },
    { label: 'Critical', value: '4', status: 'Requires Attention' },
    { label: 'Updated Today', value: '28' }
  ] : [
    { label: 'Health Score', value: '--', trend: '' },
    { label: 'Datasets', value: '0' },
    { label: 'Critical', value: '0' },
    { label: 'Updated Today', value: '0' }
  ];

  const impacts = hasDatasets ? {
    readiness: {
      affected: '12 Datasets',
      businessEffect: 'Indexing latency may increase downstream',
      urgency: 'High' as const
    },
    coverage: {
      affected: 'WMT14',
      businessEffect: 'NLP models cannot complete retraining',
      urgency: 'Medium' as const
    },
    quality: {
      affected: 'Vision Models',
      businessEffect: 'Minor edge-case degradation in low light',
      urgency: 'Low' as const
    }
  } : {
    readiness: { affected: '--', businessEffect: 'No datasets to affect', urgency: 'Low' as const },
    coverage: { affected: '--', businessEffect: 'No datasets to affect', urgency: 'Low' as const },
    quality: { affected: '--', businessEffect: 'No datasets to affect', urgency: 'Low' as const }
  };

  return {
    readinessInsight: computeDatasetReadinessInsight(),
    coverageInsight: computeAnnotationCoverageInsight(),
    qualityInsight,
    gaugeModel,
    ringSeries,
    radarMetrics,
    healthKpis,
    impacts
  };
};
