import type { Dataset } from './types';

// Raw Dataset List
export const mockDatasets: Dataset[] = [
  {
    id: 'ds_coco_2017',
    name: 'COCO 2017',
    description: 'Common Objects in Context',
    type: 'image',
    sizeBytes: 19327352832,
    createdAt: '2023-01-15T08:00:00Z',
    updatedAt: '2023-11-20T14:30:00Z',
    status: 'READY',
    samples: 330000
  },
  {
    id: 'ds_imagenet_1k',
    name: 'ImageNet-1K',
    description: 'ImageNet Large Scale Visual Recognition Challenge',
    type: 'image',
    sizeBytes: 150323855360,
    createdAt: '2022-10-01T00:00:00Z',
    updatedAt: '2024-02-12T09:15:00Z',
    status: 'READY',
    samples: 1281167
  },
  {
    id: 'ds_kitti',
    name: 'KITTI Vision Benchmark Suite',
    description: 'Autonomous driving dataset',
    type: 'video',
    sizeBytes: 42949672960,
    createdAt: '2023-05-11T11:20:00Z',
    updatedAt: '2023-09-01T16:45:00Z',
    status: 'INDEXING',
    samples: 14999
  },
  {
    id: 'ds_wmt14',
    name: 'WMT 2014 English-German',
    description: 'Machine translation dataset',
    type: 'text',
    sizeBytes: 2147483648,
    createdAt: '2024-01-05T10:00:00Z',
    updatedAt: '2024-01-06T12:00:00Z',
    status: 'READY',
    samples: 4500000
  }
];

// Hierarchy for the Sunburst Chart
export const mockDatasetHierarchy = {
  name: 'Atlas',
  children: [
    {
      name: 'Datasets',
      children: [
        {
          name: 'COCO 2017',
          children: [
            {
              name: 'YOLOv11',
              children: [
                {
                  name: 'Detection Benchmark',
                  children: [
                    {
                      name: 'Evaluation',
                      children: [
                        {
                          name: 'Experiment Alpha',
                          value: 10
                        }
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        },
        {
          name: 'ImageNet',
          children: [
            {
              name: 'ResNet50',
              children: [
                {
                  name: 'Classification Benchmark',
                  children: [
                    {
                      name: 'Eval Run 1',
                      children: [
                        { name: 'Exp A', value: 8 },
                        { name: 'Exp B', value: 12 }
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
};
