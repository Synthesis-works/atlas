import { computeTypeDistributionInsight } from '../intelligence/analytics';
import { selectDatasetTypes } from '../selectors/analytics';

export const buildAnalyticsPresentation = () => {
  const insight = computeTypeDistributionInsight();
  const types = selectDatasetTypes();

  const pieSeries = types.map(t => ({
    id: t.id,
    label: t.label,
    value: t.value
  }));

  const analyticsKpis = [
    { label: 'Total Volume', value: '1.4 PB', trend: '+12%' },
    { label: 'Synthetic Share', value: '42%', trend: '+8%' },
    { label: 'Avg Sample Size', value: '1.2 MB' },
    { label: 'Modalities', value: '5', status: 'Stable' }
  ];

  const impacts = {
    distribution: {
      affected: 'Model Training Budgets',
      businessEffect: 'Synthetic data is lowering cost-per-epoch but requires closer quality monitoring.',
      urgency: 'Medium' as const
    }
  };

  return {
    distributionInsight: insight,
    pieSeries,
    analyticsKpis,
    impacts
  };
};
