import { selectAllDatasets } from '../selectors/health';

export const selectDatasetTypes = () => {
  const datasets = selectAllDatasets();
  const types = datasets.reduce((acc, ds) => {
    acc[ds.type] = (acc[ds.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return [
    { id: 'image', label: 'Images', value: types['image'] || 0 },
    { id: 'video', label: 'Video', value: types['video'] || 0 },
    { id: 'text', label: 'Text', value: types['text'] || 0 }
  ];
};
