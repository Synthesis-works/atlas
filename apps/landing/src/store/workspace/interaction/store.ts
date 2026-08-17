import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Represents the current selection state within a workspace.
 */
export interface SelectionState {
  /** Array of currently selected item IDs */
  selectedIds: string[];
  /** The most recently selected item ID, used as the anchor for range selections */
  lastSelectedId: string | null;
  /** Whether the workspace is currently in comparison mode */
  comparisonMode: boolean;
}

/**
 * Represents the view layout and preview state of the workspace.
 */
export interface ViewState {
  /** ID of the item currently being previewed in the side panel */
  previewId: string | null;
  /** The active tab within the preview panel (e.g., 'overview', 'lineage') */
  activePreviewTab: string;
  /** The current width of the resizable side panel in pixels */
  panelWidth: number;
}

/**
 * Represents the scroll and navigation memory of the workspace.
 */
export interface NavigationState {
  /** The vertical scroll position of the main catalog list */
  scrollPosition: number;
  /** Array of IDs representing currently expanded hierarchical nodes */
  expandedIds: string[];
}

/**
 * The complete interaction state for a single workspace namespace.
 */
export interface WorkspaceInteractionState {
  selection: SelectionState;
  view: ViewState;
  navigation: NavigationState;
}

const DEFAULT_WORKSPACE_STATE: WorkspaceInteractionState = {
  selection: { selectedIds: [], lastSelectedId: null, comparisonMode: false },
  view: { previewId: null, activePreviewTab: 'overview', panelWidth: 400 },
  navigation: { scrollPosition: 0, expandedIds: [] }
};

/**
 * The root store interface containing all workspace states and actions.
 */
interface RootStore {
  /** Dictionary of workspace states keyed by their namespace (e.g., 'datasets', 'models') */
  workspaces: Record<string, WorkspaceInteractionState>;
  
  // Actions
  /** Initializes a workspace namespace if it does not already exist */
  initWorkspace: (ns: string) => void;
  /** Resets a workspace namespace back to the default state */
  resetWorkspace: (ns: string) => void;
  
  // Selection Actions
  /** Selects an item. If multi is true, toggles the item in the selection array */
  selectItem: (ns: string, id: string, multi?: boolean) => void;
  /** Performs a shift-click range selection between the last selected item and the target */
  rangeSelect: (ns: string, targetId: string, visibleIds: string[]) => void;
  /** Clears all current selections in the workspace */
  clearSelection: (ns: string) => void;
  /** Toggles comparison mode for the workspace */
  setComparisonMode: (ns: string, active: boolean) => void;

  // View Actions
  /** Opens the preview panel for a specific item */
  openPreview: (ns: string, id: string) => void;
  /** Closes the active preview panel */
  closePreview: (ns: string) => void;
  /** Sets the active tab within the preview panel */
  setActivePreviewTab: (ns: string, tab: string) => void;
  /** Adjusts the width of the preview panel */
  setPanelWidth: (ns: string, width: number) => void;

  // Navigation Actions
  /** Saves the vertical scroll position for restoring when navigating back */
  setScrollPosition: (ns: string, pos: number) => void;
  /** Toggles the expansion state of a hierarchical node */
  toggleExpanded: (ns: string, id: string) => void;

  // Intent Actions
  /** 
   * Resolves the Escape key intent based on interaction hierarchy (Modal -> Drawer -> Preview -> Selection).
   * Returns true if the event was consumed, allowing the caller to conditionally preventDefault.
   */
  handleEscapeIntent: (ns: string) => boolean;
}

/**
 * Interfaces defining the strict shape of persisted data.
 */
interface PersistedWorkspaceState {
  view: {
    activePreviewTab: string;
    panelWidth: number;
  };
}

interface PersistedRootState {
  workspaces: Record<string, PersistedWorkspaceState>;
}

/**
 * Global Workspace Interaction Store.
 * 
 * Manages transient and persistent UI state (selection, navigation, preview) 
 * isolated by workspace namespace (e.g., 'datasets', 'models').
 * Implements persistence middleware to restore layouts across sessions.
 */
export const useWorkspaceInteractionStore = create<RootStore>()(
  persist(
    (set) => ({
      workspaces: {},
      
      initWorkspace: (ns) => set((state) => {
        if (!state.workspaces[ns]) {
          return { workspaces: { ...state.workspaces, [ns]: DEFAULT_WORKSPACE_STATE } };
        }
        return state;
      }),

      resetWorkspace: (ns) => set((state) => ({
        workspaces: { ...state.workspaces, [ns]: DEFAULT_WORKSPACE_STATE }
      })),

      selectItem: (ns, id, multi = false) => set((state) => {
        const ws = state.workspaces[ns] || DEFAULT_WORKSPACE_STATE;
        let newSelected = [...ws.selection.selectedIds];
        
        if (multi) {
          if (newSelected.includes(id)) {
            newSelected = newSelected.filter(i => i !== id);
          } else {
            newSelected.push(id);
          }
        } else {
          newSelected = newSelected.includes(id) && newSelected.length === 1 ? [] : [id];
        }

        return {
          workspaces: {
            ...state.workspaces,
            [ns]: {
              ...ws,
              selection: { ...ws.selection, selectedIds: newSelected, lastSelectedId: id }
            }
          }
        };
      }),

      rangeSelect: (ns, targetId, visibleIds) => set((state) => {
        const ws = state.workspaces[ns] || DEFAULT_WORKSPACE_STATE;
        const lastId = ws.selection.lastSelectedId;
        
        if (!lastId) {
          return {
            workspaces: {
              ...state.workspaces,
              [ns]: { ...ws, selection: { ...ws.selection, selectedIds: [targetId], lastSelectedId: targetId } }
            }
          };
        }

        const startIndex = visibleIds.indexOf(lastId);
        const endIndex = visibleIds.indexOf(targetId);

        if (startIndex === -1 || endIndex === -1) return state;

        const start = Math.min(startIndex, endIndex);
        const end = Math.max(startIndex, endIndex);
        const range = visibleIds.slice(start, end + 1);

        // Add range to existing selection, avoiding duplicates
        const newSelected = Array.from(new Set([...ws.selection.selectedIds, ...range]));

        return {
          workspaces: {
            ...state.workspaces,
            [ns]: { ...ws, selection: { ...ws.selection, selectedIds: newSelected } }
          }
        };
      }),

      clearSelection: (ns) => set((state) => {
        const ws = state.workspaces[ns];
        if (!ws) return state;
        return {
          workspaces: {
            ...state.workspaces,
            [ns]: { ...ws, selection: { ...ws.selection, selectedIds: [], lastSelectedId: null } }
          }
        };
      }),

      setComparisonMode: (ns, active) => set((state) => {
        const ws = state.workspaces[ns];
        if (!ws) return state;
        return {
          workspaces: {
            ...state.workspaces,
            [ns]: { ...ws, selection: { ...ws.selection, comparisonMode: active } }
          }
        };
      }),

      openPreview: (ns, id) => set((state) => {
        const ws = state.workspaces[ns] || DEFAULT_WORKSPACE_STATE;
        // Opening preview cancels active hover state (handled by UI, since hover is transient)
        // Ensure defaults if opening a DIFFERENT dataset
        const isSame = ws.view.previewId === id;
        
        return {
          workspaces: {
            ...state.workspaces,
            [ns]: {
              ...ws,
              view: {
                ...ws.view,
                previewId: id,
                // Reset active tab if opening new dataset, else persist
                activePreviewTab: isSame ? ws.view.activePreviewTab : 'overview'
              },
              navigation: {
                ...ws.navigation,
                // Reset expanded if opening new dataset
                expandedIds: isSame ? ws.navigation.expandedIds : []
              }
            }
          }
        };
      }),

      closePreview: (ns) => set((state) => {
        const ws = state.workspaces[ns];
        if (!ws) return state;
        return {
          workspaces: {
            ...state.workspaces,
            [ns]: { ...ws, view: { ...ws.view, previewId: null } }
          }
        };
      }),

      setActivePreviewTab: (ns, tab) => set((state) => {
        const ws = state.workspaces[ns];
        if (!ws) return state;
        return {
          workspaces: {
            ...state.workspaces,
            [ns]: { ...ws, view: { ...ws.view, activePreviewTab: tab } }
          }
        };
      }),

      setPanelWidth: (ns, width) => set((state) => {
        const ws = state.workspaces[ns];
        if (!ws) return state;
        return {
          workspaces: {
            ...state.workspaces,
            [ns]: { ...ws, view: { ...ws.view, panelWidth: width } }
          }
        };
      }),

      setScrollPosition: (ns, pos) => set((state) => {
        const ws = state.workspaces[ns];
        if (!ws) return state;
        return {
          workspaces: {
            ...state.workspaces,
            [ns]: { ...ws, navigation: { ...ws.navigation, scrollPosition: pos } }
          }
        };
      }),

      toggleExpanded: (ns, id) => set((state) => {
        const ws = state.workspaces[ns];
        if (!ws) return state;
        const isExpanded = ws.navigation.expandedIds.includes(id);
        const nextIds = isExpanded 
          ? ws.navigation.expandedIds.filter(i => i !== id)
          : [...ws.navigation.expandedIds, id];
          
        return {
          workspaces: {
            ...state.workspaces,
            [ns]: { ...ws, navigation: { ...ws.navigation, expandedIds: nextIds } }
          }
        };
      }),

      handleEscapeIntent: (ns) => {
        let consumed = false;
        
        set((state) => {
          const ws = state.workspaces[ns];
          if (!ws) return state;
          
          // Hierarchy Level 1: Previews (Highest Priority currently implemented)
          if (ws.view.previewId) {
            consumed = true;
            return {
              workspaces: {
                ...state.workspaces,
                [ns]: { ...ws, view: { ...ws.view, previewId: null } }
              }
            };
          }
          
          // Hierarchy Level 2: Selection
          if (ws.selection.selectedIds.length > 0) {
            consumed = true;
            return {
              workspaces: {
                ...state.workspaces,
                [ns]: { ...ws, selection: { ...ws.selection, selectedIds: [], lastSelectedId: null } }
              }
            };
          }
          
          return state;
        });

        return consumed;
      }
    }),
    {
      name: 'atlas-interaction-storage',
      version: 1,
      migrate: (persistedState: unknown, _version: number) => {
        // Example schema evolution: if (_version === 0) { ...migrate }
        return persistedState as PersistedRootState;
      },
      // ONLY persist these specific fields (private state). 
      // Do NOT persist selection or hover.
      partialize: (state): PersistedRootState => {
        const persistedWorkspaces: Record<string, PersistedWorkspaceState> = {};
        for (const [ns, ws] of Object.entries(state.workspaces)) {
          persistedWorkspaces[ns] = {
            view: {
              activePreviewTab: ws.view.activePreviewTab,
              panelWidth: ws.view.panelWidth
            }
          };
        }
        return { workspaces: persistedWorkspaces };
      },
      merge: (persistedState: unknown, currentState: RootStore) => {
        // Hydrate persisted state into defaults safely
        const state = persistedState as Partial<PersistedRootState> | null;
        const mergedWorkspaces = { ...currentState.workspaces };
        
        if (state && typeof state === 'object' && state.workspaces) {
          for (const [ns, pWs] of Object.entries(state.workspaces)) {
            if (pWs && pWs.view) {
              mergedWorkspaces[ns] = {
                ...DEFAULT_WORKSPACE_STATE,
                view: { ...DEFAULT_WORKSPACE_STATE.view, ...pWs.view }
              };
            }
          }
        }
        return { ...currentState, workspaces: mergedWorkspaces };
      }
    }
  )
);
