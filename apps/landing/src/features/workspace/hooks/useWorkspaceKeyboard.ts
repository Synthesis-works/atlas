import { useEffect } from 'react';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';

/**
 * Props for configuring the global workspace keyboard listener.
 */
export interface UseWorkspaceKeyboardProps {
  /** The namespace of the workspace to control (e.g., 'datasets') */
  namespace: string;
  /** Array of visible item IDs in the catalog to allow Arrow navigation */
  itemIds: string[];
  /** Reference to the container element; arrow keys only work when focus is inside this container */
  containerRef: React.RefObject<HTMLElement | null>;
  /** Reference to the search input element to focus on '/' press */
  searchRef?: React.RefObject<HTMLInputElement | null>;
}

/**
 * Global keyboard listener for workspace interactions.
 * Handles Arrow navigation, Enter (preview), Escape (close/clear), and '/' (search).
 * Automatically respects input boundaries (does not hijack typing).
 */
export function useWorkspaceKeyboard({ namespace, itemIds, containerRef, searchRef }: UseWorkspaceKeyboardProps) {
  const ws = useWorkspaceInteractionStore(s => s.workspaces[namespace]);
  const selectItem = useWorkspaceInteractionStore(s => s.selectItem);
  const openPreview = useWorkspaceInteractionStore(s => s.openPreview);
  const handleEscapeIntent = useWorkspaceInteractionStore(s => s.handleEscapeIntent);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Helper to determine if user is currently typing in an input
      const isTypingInInput = () => {
        const active = document.activeElement as HTMLElement | null;
        if (!active) return false;
        
        const tagName = active.tagName;
        const isTextInput = tagName === 'INPUT' || tagName === 'TEXTAREA';
        const isContentEditable = active.isContentEditable;
        
        // Ensure we aren't intercepting code editors or standard text inputs
        return isTextInput || isContentEditable || active.closest('.monaco-editor') !== null;
      };

      const typing = isTypingInInput();

      // 1. "/" Search Focus (only if not already typing)
      if (e.key === '/' && !typing) {
        e.preventDefault();
        searchRef?.current?.focus();
        return;
      }

      // 2. Escape: Dispatch Interaction Intent
      if (e.key === 'Escape') {
        const consumed = handleEscapeIntent(namespace);
        if (consumed) {
          e.preventDefault();
        }
        return;
      }

      // 3. Arrow Keys / Enter (List Navigation)
      // Only process these if focus is within the workspace container AND user is not typing
      const isWithinContainer = containerRef.current?.contains(document.activeElement as Node);
      
      if (!isWithinContainer || typing) {
        return;
      }

      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault(); // Prevent page scrolling
        
        const currentSelected = ws?.selection.lastSelectedId;
        let nextIndex = 0;

        if (currentSelected) {
          const currentIndex = itemIds.indexOf(currentSelected);
          if (currentIndex !== -1) {
            nextIndex = e.key === 'ArrowDown' 
              ? Math.min(currentIndex + 1, itemIds.length - 1)
              : Math.max(currentIndex - 1, 0);
          }
        }
        
        const nextId = itemIds[nextIndex];
        if (nextId) {
          selectItem(namespace, nextId, e.shiftKey || e.ctrlKey || e.metaKey);
        }
      }

      if (e.key === 'Enter') {
        e.preventDefault();
        const currentSelected = ws?.selection.lastSelectedId;
        if (currentSelected) {
          openPreview(namespace, currentSelected);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [namespace, itemIds, containerRef, searchRef, ws, selectItem, openPreview, handleEscapeIntent]);
}
