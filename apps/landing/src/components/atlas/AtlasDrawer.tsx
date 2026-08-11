import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface AtlasDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  width?: string;
}

export function AtlasDrawer({ isOpen, onClose, title, children, width = '450px' }: AtlasDrawerProps) {
  
  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[200]"
          />
          
          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: "tween", ease: "easeInOut", duration: 0.25 }}
            style={{ width }}
            className="fixed top-0 right-0 h-full bg-neutral-900 border-l border-white/10 z-[201] flex flex-col shadow-2xl"
          >
            {title && (
              <div className="flex items-center justify-between p-6 border-b border-white/10 shrink-0">
                <h3 className="text-white text-xl font-medium">{title}</h3>
                <button 
                  onClick={onClose}
                  className="p-2 text-white/40 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6l-12 12M6 6l12 12"/></svg>
                </button>
              </div>
            )}
            <div className="flex-1 overflow-y-auto">
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
