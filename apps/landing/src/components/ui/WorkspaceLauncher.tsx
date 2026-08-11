import React, { useEffect, useState, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FolderKanban, 
  Cpu, 
  Database, 
  Server, 
  FlaskConical,
  Search,
  Command,
  LayoutDashboard
} from 'lucide-react';

export type CommandItem = {
  id: string;
  type: 'navigation' | 'action';
  title: string;
  description?: string;
  icon: React.ReactNode;
  action: (navigate: ReturnType<typeof useNavigate>) => void;
};

const NAVIGATION_COMMANDS: CommandItem[] = [
  {
    id: 'nav-overview',
    type: 'navigation',
    title: 'Overview',
    description: 'Return to dashboard home',
    icon: <LayoutDashboard className="w-5 h-5" />,
    action: (nav) => nav('/dashboard')
  },
  {
    id: 'nav-datasets',
    type: 'navigation',
    title: 'Datasets',
    description: 'Browse datasets',
    icon: <FolderKanban className="w-5 h-5" />,
    action: (nav) => nav('/dashboard/datasets')
  },
  {
    id: 'nav-models',
    type: 'navigation',
    title: 'Models',
    description: 'Browse AI models',
    icon: <Cpu className="w-5 h-5" />,
    action: (nav) => nav('/dashboard/models')
  },
  {
    id: 'nav-benchmarks',
    type: 'navigation',
    title: 'Benchmarks',
    description: 'View benchmark suites',
    icon: <Database className="w-5 h-5" />,
    action: (nav) => nav('/dashboard/benchmarks')
  },
  {
    id: 'nav-providers',
    type: 'navigation',
    title: 'Providers',
    description: 'Manage providers',
    icon: <Server className="w-5 h-5" />,
    action: (nav) => nav('/dashboard/providers')
  },
  {
    id: 'nav-experiments',
    type: 'navigation',
    title: 'Experiments',
    description: 'View experiment runs',
    icon: <FlaskConical className="w-5 h-5" />,
    action: (nav) => nav('/dashboard/experiments')
  },
  {
    id: 'action-fleet-commands',
    type: 'action',
    title: 'Fleet Command Palette',
    description: 'Open fleet operations palette',
    icon: <Cpu className="w-5 h-5" />,
    action: (nav) => {
      if (window.location.pathname !== '/dashboard/models') {
        nav('/dashboard/models');
        setTimeout(() => {
          window.dispatchEvent(new Event('open-fleet-commands'));
        }, 150);
      } else {
        window.dispatchEvent(new Event('open-fleet-commands'));
      }
    }
  }
];

// Simple fuzzy search
function fuzzyMatch(pattern: string, str: string) {
  let patternIdx = 0;
  let strIdx = 0;
  const patternLen = pattern.length;
  const strLen = str.length;
  const lowerPattern = pattern.toLowerCase();
  const lowerStr = str.toLowerCase();

  while (patternIdx < patternLen && strIdx < strLen) {
    if (lowerPattern[patternIdx] === lowerStr[strIdx]) {
      patternIdx++;
    }
    strIdx++;
  }
  return patternIdx === patternLen;
}

export function WorkspaceLauncher() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [recentIds, setRecentIds] = useState<string[]>([]);
  const navigate = useNavigate();
  
  const inputRef = useRef<HTMLInputElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // Load recent from local storage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('atlas_recent_workspaces');
      if (stored) {
        setRecentIds(JSON.parse(stored));
      }
    } catch (e) {
      // ignore
    }
  }, []);

  const saveRecent = (id: string) => {
    try {
      const updated = [id, ...recentIds.filter(i => i !== id)].slice(0, 3);
      setRecentIds(updated);
      localStorage.setItem('atlas_recent_workspaces', JSON.stringify(updated));
    } catch (e) {
      // ignore
    }
  };

  // Global Keyboard Listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsOpen((prev) => {
          if (!prev) {
            previousFocusRef.current = document.activeElement as HTMLElement;
          }
          return !prev;
        });
      }
    };
    window.addEventListener('keydown', handleKeyDown, true);
    return () => window.removeEventListener('keydown', handleKeyDown, true);
  }, []);

  // Filter commands
  const filteredCommands = useMemo(() => {
    if (!query) {
      // When empty, show Recent first, then the rest
      const recent = recentIds.map(id => NAVIGATION_COMMANDS.find(c => c.id === id)).filter(Boolean) as CommandItem[];
      const rest = NAVIGATION_COMMANDS.filter(c => !recentIds.includes(c.id));
      return [...recent, ...rest];
    }
    return NAVIGATION_COMMANDS.filter(c => fuzzyMatch(query, c.title) || fuzzyMatch(query, c.description || ''));
  }, [query, recentIds]);

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Manage focus and scroll
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50); // slight delay for animation
    } else {
      setQuery('');
      setSelectedIndex(0);
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
        previousFocusRef.current = null;
      }
    }
  }, [isOpen]);

  const handleExecute = (cmd: CommandItem) => {
    saveRecent(cmd.id);
    setIsOpen(false);
    cmd.action(navigate);
  };

  const handleModalKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      setIsOpen(false);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % filteredCommands.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredCommands.length) % filteredCommands.length);
    } else if (e.key === 'Enter' && filteredCommands.length > 0) {
      e.preventDefault();
      handleExecute(filteredCommands[selectedIndex]);
    }
  };

  // Group commands for rendering (for now just all in one group, or separated by Recent)
  const isSearchEmpty = query === '';
  const recentCommands = isSearchEmpty ? filteredCommands.filter(c => recentIds.includes(c.id)) : [];
  const otherCommands = isSearchEmpty ? filteredCommands.filter(c => !recentIds.includes(c.id)) : filteredCommands;

  let globalIndex = 0;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 bg-[#0A0C10]/80 backdrop-blur-sm z-50"
            onClick={() => setIsOpen(false)}
          />
          <div className="fixed inset-0 flex items-start justify-center pt-[15vh] z-50 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: -10 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              className="w-full max-w-xl bg-[#111318] border border-white/10 shadow-2xl rounded-xl overflow-hidden pointer-events-auto flex flex-col"
              onKeyDown={handleModalKeyDown}
            >
              {/* Search Header */}
              <div className="flex items-center px-4 py-3 border-b border-white/10 bg-[#16181D]">
                <Search className="w-5 h-5 text-white/40 mr-3 shrink-0" />
                <input
                  ref={inputRef}
                  type="text"
                  placeholder="Search Atlas..."
                  className="flex-1 bg-transparent border-none text-white placeholder-white/30 focus:outline-none focus:ring-0 text-base"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <div className="flex items-center gap-2 bg-white/5 px-2 py-1 rounded text-[10px] text-white/30 font-medium font-mono shrink-0">
                  <span className="flex items-center gap-0.5"><Command className="w-3 h-3" /> K</span>
                  <span className="text-white/20 italic">or</span>
                  <span>Ctrl K</span>
                </div>
              </div>

              {/* Command List */}
              <div className="max-h-[60vh] overflow-y-auto p-2">
                {filteredCommands.length === 0 ? (
                  <div className="py-12 text-center text-sm text-white/40">
                    <p>No workspace found.</p>
                    <p className="mt-1">Try another search.</p>
                  </div>
                ) : (
                  <>
                    {recentCommands.length > 0 && (
                      <div className="mb-2">
                        <div className="px-3 py-1.5 text-xs font-semibold text-white/30 uppercase tracking-wider">
                          Recent
                        </div>
                        {recentCommands.map((cmd) => {
                          const isSelected = globalIndex === selectedIndex;
                          const currentIndex = globalIndex++;
                          return (
                            <CommandRow 
                              key={cmd.id} 
                              cmd={cmd} 
                              isSelected={isSelected} 
                              onHover={() => setSelectedIndex(currentIndex)}
                              onClick={() => handleExecute(cmd)} 
                            />
                          );
                        })}
                      </div>
                    )}

                    {otherCommands.length > 0 && (
                      <div>
                        {isSearchEmpty && recentCommands.length > 0 && (
                          <div className="px-3 py-1.5 text-xs font-semibold text-white/30 uppercase tracking-wider mt-2 border-t border-white/5 pt-3">
                            Workspaces
                          </div>
                        )}
                        {otherCommands.map((cmd) => {
                          const isSelected = globalIndex === selectedIndex;
                          const currentIndex = globalIndex++;
                          return (
                            <CommandRow 
                              key={cmd.id} 
                              cmd={cmd} 
                              isSelected={isSelected} 
                              onHover={() => setSelectedIndex(currentIndex)}
                              onClick={() => handleExecute(cmd)} 
                            />
                          );
                        })}
                      </div>
                    )}
                  </>
                )}
              </div>
              
              {/* Footer */}
              <div className="px-4 py-2 border-t border-white/5 bg-[#16181D] flex items-center justify-between text-[10px] text-white/30 font-medium">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1">
                    <kbd className="bg-white/10 px-1.5 py-0.5 rounded">↑</kbd>
                    <kbd className="bg-white/10 px-1.5 py-0.5 rounded">↓</kbd>
                    to navigate
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="bg-white/10 px-1.5 py-0.5 rounded">Enter</kbd>
                    to select
                  </span>
                </div>
                <span className="flex items-center gap-1">
                  <kbd className="bg-white/10 px-1.5 py-0.5 rounded">Esc</kbd>
                  to close
                </span>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}

function CommandRow({ cmd, isSelected, onHover, onClick }: { cmd: CommandItem, isSelected: boolean, onHover: () => void, onClick: () => void }) {
  const domRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (isSelected && domRef.current) {
      domRef.current.scrollIntoView({ block: 'nearest' });
    }
  }, [isSelected]);

  return (
    <div
      ref={domRef}
      className={`
        flex items-center px-3 py-3 mx-1 my-0.5 rounded-lg cursor-pointer transition-colors
        ${isSelected ? 'bg-indigo-500/20 text-white' : 'text-white/60 hover:bg-white/5'}
      `}
      onMouseMove={onHover}
      onClick={onClick}
    >
      <div className={`mr-3 p-2 rounded-md ${isSelected ? 'bg-indigo-500/30 text-indigo-300' : 'bg-white/5 text-white/50'}`}>
        {cmd.icon}
      </div>
      <div className="flex flex-col flex-1">
        <span className="text-sm font-medium">{cmd.title}</span>
        {cmd.description && <span className={`text-xs ${isSelected ? 'text-indigo-200/70' : 'text-white/30'}`}>{cmd.description}</span>}
      </div>
    </div>
  );
}
