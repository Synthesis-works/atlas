import type { ChartConfig } from '@/shared/charts';

export const CATEGORY_DISTRIBUTION_CHART: ChartConfig = {
  type: 'donut',
  data: [
    { label: 'Reasoning', value: 38, color: '#a78bfa' },
    { label: 'Coding', value: 28, color: '#34d399' },
    { label: 'Math', value: 22, color: '#60a5fa' },
    { label: 'Safety', value: 18, color: '#f43f5e' },
    { label: 'Knowledge', value: 24, color: '#818cf8' },
    { label: 'Agents', value: 18, color: '#fb923c' },
  ],
};

export const VERIFICATION_STATUS_CHART: ChartConfig = {
  type: 'stacked-bar',
  data: [
    { label: 'Verified (9/9)', value: 118, color: '#34d399' },
    { label: 'Validating', value: 22, color: '#fbbf24' },
    { label: 'Draft / Pending', value: 8, color: '#94a3b8' },
  ],
};

export const RUNTIME_BAR_CHART: ChartConfig = {
  type: 'bar',
  data: [
    { label: 'Agents', value: 2700, color: '#fb923c' },
    { label: 'ARC-Challenge', value: 1104, color: '#a78bfa' },
    { label: 'MMLU-Pro', value: 888, color: '#818cf8' },
    { label: 'AGIEval', value: 552, color: '#60a5fa' },
    { label: 'HumanEval', value: 210, color: '#34d399' },
  ],
};
