import { computeHierarchyInsight } from '../intelligence/hierarchy';
import { selectDatasetHierarchy } from '../selectors/hierarchy';

export const buildHierarchyPresentation = () => {
  return {
    insight: computeHierarchyInsight(),
    tree: selectDatasetHierarchy()
  };
};
