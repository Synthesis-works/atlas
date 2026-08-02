import { motion } from 'framer-motion';
import { useDatasetCatalog } from '../../hooks/useDatasetCatalog';

export function AtlasDatasetComparison({ catalog }: { catalog: ReturnType<typeof useDatasetCatalog> }) {
  const { comparisonModels } = catalog;

  // Comparison is only valid when exactly 2 datasets are selected
  if (catalog.selectedIds.length !== 2 || comparisonModels.length !== 2) return null;

  return (
    <motion.div 
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: 50, opacity: 0 }}
      className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[800px] bg-neutral-900 border border-white/20 rounded-2xl shadow-2xl p-6 z-50 flex flex-col gap-6"
    >
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <h3 className="text-white text-lg font-medium">Dataset Comparison</h3>
        <button className="text-white/40 hover:text-white" onClick={catalog.handleClearSelection}>
          Close
        </button>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {comparisonModels.map((model) => (
          <div key={model.id} className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <img src={model.thumbnailUrl} className="w-12 h-12 rounded bg-white/5 object-cover" />
              <div>
                <h4 className="text-white font-medium">{model.name}</h4>
                <p className="text-white/50 text-xs">{model.version}</p>
              </div>
            </div>

            <div className="flex flex-col gap-2 text-sm">
              <div className="flex justify-between py-2 border-b border-white/5">
                <span className="text-white/50">Storage</span>
                <span className="text-white">{model.sizeFormatted}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-white/5">
                <span className="text-white/50">Samples</span>
                <span className="text-white">{model.samplesFormatted}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-white/5">
                <span className="text-white/50">Health Score</span>
                <span className="text-white">{model.healthScore}%</span>
              </div>
              <div className="flex justify-between py-2 border-b border-white/5">
                <span className="text-white/50">Duplicates</span>
                <span className="text-white">{model.duplicateCount}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-white/5">
                <span className="text-white/50">Annotations</span>
                <span className="text-white">{model.annotationCoverage}%</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
