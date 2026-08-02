import { computeStorageCapacityInsight } from '../intelligence/storage';

export const buildStoragePresentation = () => {
  const insight = computeStorageCapacityInsight();

  const gaugeModel = {
    id: 'storage_gauge',
    score: 68,
    total: 100, // Total Capacity %
    label: 'Capacity Used'
  };

  const lineData = [
    { date: '2023-01-01', growth: 12 },
    { date: '2023-02-01', growth: 14 },
    { date: '2023-03-01', growth: 14.5 },
    { date: '2023-04-01', growth: 16.2 },
    { date: '2023-05-01', growth: 18.2 }
  ];

  const lineSeries = [
    {
      id: 'growth',
      name: 'Storage Growth',
      color: '#3B82F6',
      data: lineData
    }
  ];

  const storageKpis = [
    { label: 'Total Storage', value: '4.2 PB', trend: '+140 TB' },
    { label: 'Cost/Month', value: '$12,450', trend: '+$450', status: 'Warning' },
    { label: 'Archivable', value: '850 TB' },
    { label: 'Fastest Growing', value: 'Lidar Scans' }
  ];

  const impacts = {
    capacity: {
      affected: 'Cloud Storage Budget',
      businessEffect: 'Projected to exceed Q3 allocation by 15% if trend continues.',
      urgency: 'Medium' as const
    }
  };

  return {
    capacityInsight: insight,
    gaugeModel,
    lineData,
    lineSeries,
    storageKpis,
    impacts
  };
};
