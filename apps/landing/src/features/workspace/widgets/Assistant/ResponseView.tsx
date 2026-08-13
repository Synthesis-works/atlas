import { useRef, useEffect } from 'react';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface ResponseViewProps {
  messages: Message[];
  isLoading: boolean;
}

export function ResponseView({ messages, isLoading }: ResponseViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0 select-text"
      style={{ maxHeight: 'calc(360px - 48px - 72px)' }}
    >
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-center py-6">
          <p className="text-xs text-white/50 font-medium">Hello, I'm the Atlas Evaluator Assistant.</p>
          <p className="text-[10px] text-white/20 mt-1 max-w-[200px]">
            Ask me to summarize evaluations, suggest optimization metrics, or write code.
          </p>
        </div>
      ) : (
        messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.role === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-indigo-500/12 border border-indigo-500/20 text-white'
                  : 'bg-white/[0.03] border border-white/[0.06] text-white/80'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))
      )}

      {isLoading && (
        <div className="flex items-start gap-2">
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2.5 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      )}
    </div>
  );
}
