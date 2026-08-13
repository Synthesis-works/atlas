import type { ModelCapabilityTag } from '@/domain/models/types';

const TAG_STYLES: Partial<Record<ModelCapabilityTag, string>> = {
  'Chat':             'bg-indigo-500/10 text-indigo-300 border-indigo-500/20',
  'Reasoning':        'bg-violet-500/10 text-violet-300 border-violet-500/20',
  'Vision':           'bg-pink-500/10 text-pink-300 border-pink-500/20',
  'Audio':            'bg-orange-500/10 text-orange-300 border-orange-500/20',
  'Tool Calling':     'bg-amber-500/10 text-amber-300 border-amber-500/20',
  'Embedding':        'bg-cyan-500/10 text-cyan-300 border-cyan-500/20',
  'Code':             'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
  'OCR':              'bg-teal-500/10 text-teal-300 border-teal-500/20',
  'Function Calling': 'bg-yellow-500/10 text-yellow-300 border-yellow-500/20',
  'Long Context':     'bg-blue-500/10 text-blue-300 border-blue-500/20',
  'Streaming':        'bg-purple-500/10 text-purple-300 border-purple-500/20',
  'Fine-tunable':     'bg-rose-500/10 text-rose-300 border-rose-500/20',
  'Multimodal':       'bg-fuchsia-500/10 text-fuchsia-300 border-fuchsia-500/20',
  'Agents':           'bg-sky-500/10 text-sky-300 border-sky-500/20',
};

export function CapabilityGrid({ tags }: { tags: ModelCapabilityTag[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map(tag => (
        <span
          key={tag}
          className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${
            TAG_STYLES[tag] ?? 'bg-white/[0.04] text-white/40 border-white/[0.08]'
          }`}
        >
          {tag}
        </span>
      ))}
    </div>
  );
}
