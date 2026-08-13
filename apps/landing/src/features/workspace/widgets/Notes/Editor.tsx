import { useState } from 'react';

export function Editor() {
  const [text, setText] = useState(() => {
    return localStorage.getItem('atlas_notes_content') || 'Evaluation Notes:\n- MMLU-Pro test run is looking stable.\n- Hallucination rate is within bounds (<3.2%).\n- Ready for cluster deployment.';
  });

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setText(val);
    localStorage.setItem('atlas_notes_content', val);
  };

  return (
    <div className="flex-1 p-3 min-h-0">
      <textarea
        value={text}
        onChange={handleChange}
        placeholder="Type your notes here..."
        className="w-full h-full p-2 text-xs bg-white/[0.02] border border-white/[0.05] rounded-xl outline-none text-white/80 placeholder-white/20 resize-none leading-relaxed transition-all focus:border-indigo-500/30"
        style={{ height: 'calc(240px - 48px - 24px)' }}
      />
    </div>
  );
}
