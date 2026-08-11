import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { LiquidGlassCard } from '@/design/glass/LiquidGlassCard';
import { GlassGlow } from '@/design/glass/GlassGlow';
import { Header } from './Header';
import { ResponseView, type Message } from './ResponseView';
import { PromptInput } from './PromptInput';

export function AssistantWidget() {
  const { widgetLayouts, updateWidgetLayout } = useWorkspaceStore();
  const state = widgetLayouts.assistant;

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [glowActive, setGlowActive] = useState(false);
  const [searchParams] = useSearchParams();
  const isPreviewOpen = searchParams.has('preview');

  if (!state || !state.visible) return null;

  const handlePositionChange = (x: number, y: number) => {
    updateWidgetLayout('assistant', { x, y });
  };

  const handleDragStateChange = (dragging: boolean) => {
    updateWidgetLayout('assistant', { dragging });
  };

  const handleToggleCollapse = () => {
    updateWidgetLayout('assistant', { collapsed: !state.collapsed });
  };

  const handleClose = () => {
    updateWidgetLayout('assistant', { visible: false });
  };

  const handlePromptSubmit = (prompt: string) => {
    const userMsg: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: prompt,
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    // Mock response trigger
    setTimeout(() => {
      let content = "I've checked the evaluations. GPT-5 shows a 92.8% Pass@1 rate on MMLU-Pro with latency averaging 120ms.";
      if (prompt.toLowerCase().includes('latency') || prompt.toLowerCase().includes('optimize')) {
        content = 'To optimize LLM latency, enable key-value cache quantisation (INT4) and batch prompt evaluations up to size 64.';
      } else if (prompt.toLowerCase().includes('report') || prompt.toLowerCase().includes('summary')) {
        content = 'Evaluation Report Summary:\n- Arena-Hard: Gemma-2 (100% completed)\n- MMLU-Pro: GPT-5 (78% complete, running)\n- GPQA: Claude-3.5 (41% complete)';
      }

      const aiMsg: Message = {
        id: `msg-ai-${Date.now()}`,
        role: 'assistant',
        content,
      };

      setMessages((prev) => [...prev, aiMsg]);
      setIsLoading(false);
      
      // Trigger subtle glass glow on message receive
      setGlowActive(true);
      setTimeout(() => setGlowActive(false), 1200);
    }, 1500);
  };

  return (
    <motion.div
      className="fixed inset-0 pointer-events-none z-[200]"
      animate={{ x: isPreviewOpen ? -520 : 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
    >
      <div className="pointer-events-auto">
        <LiquidGlassCard
          id="assistant"
          initialX={state.x}
          initialY={state.y}
          onPositionChange={handlePositionChange}
      onDragStateChange={handleDragStateChange}
      className="w-[min(340px,calc(100vw-2rem))] flex flex-col z-[200] rounded-lg"
      style={{
        height: state.collapsed ? 'auto' : '360px',
      }}
    >
      {/* Event Glow Indicator */}
      <GlassGlow active={glowActive} />

      <Header
        collapsed={state.collapsed}
        onToggleCollapse={handleToggleCollapse}
        onClose={handleClose}
      />

      {!state.collapsed && (
        <>
          <ResponseView messages={messages} isLoading={isLoading} />
          <PromptInput onSubmit={handlePromptSubmit} isLoading={isLoading} />
        </>
      )}
    </LiquidGlassCard>
    </div>
    </motion.div>
  );
}
