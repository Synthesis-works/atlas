import React, { useState } from 'react';
import { ArrowUp } from 'lucide-react';

interface PromptInputProps {
  onSubmit: (prompt: string) => void;
  isLoading: boolean;
}

export function PromptInput({ onSubmit, isLoading }: PromptInputProps) {
  const [value, setValue] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim() || isLoading) return;
    onSubmit(value);
    setValue('');
  };

  const suggestions = [
    'Analyze GPQA performance',
    'Optimize GPT-5 latency',
    'Create report summary',
  ];

  return (
    <div className="p-3 border-t border-white/[0.06] bg-neutral-950/20">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask Atlas AI..."
          className="flex-1 min-w-0 h-9 px-3 text-xs bg-white/[0.04] border border-white/[0.08] focus:border-indigo-500/50 rounded-lg outline-none text-white placeholder-white/25 transition-all"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={!value.trim() || isLoading}
          className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/35 hover:text-white transition-all disabled:opacity-40 disabled:hover:bg-indigo-500/20 disabled:hover:text-indigo-300 cursor-pointer"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </form>

      <div className="flex gap-1.5 overflow-x-auto no-scrollbar mt-2 pb-0.5">
        {suggestions.map((text) => (
          <button
            key={text}
            type="button"
            onClick={() => setValue(text)}
            className="flex-shrink-0 px-2 py-1 text-[10px] bg-white/[0.02] hover:bg-white/[0.06] border border-white/[0.05] rounded-md text-white/40 hover:text-white/70 transition-colors cursor-pointer"
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}
