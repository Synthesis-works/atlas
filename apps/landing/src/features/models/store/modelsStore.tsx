/**
 * Models Feature Store
 * Reactive state for the Models Registry page.
 */

import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import type { RegistryModel, ModelStatus } from '@/domain/models/types';
import { MOCK_MODELS } from '@/domain/models/mock';

interface ModelsStoreCtx {
  models: RegistryModel[];
  search: string;
  statusFilter: ModelStatus | 'all';
  providerFilter: string;
  selectedModel: RegistryModel | null;
  drawerOpen: boolean;
  drawerTab: string;
  compareIds: string[];
  commandPaletteOpen: boolean;
  activeWorkloadTab: string;
  setSearch: (v: string) => void;
  setStatusFilter: (v: ModelStatus | 'all') => void;
  setProviderFilter: (v: string) => void;
  openDrawer: (model: RegistryModel, tab?: string) => void;
  closeDrawer: () => void;
  setDrawerTab: (tab: string) => void;
  toggleCompare: (id: string) => void;
  clearCompare: () => void;
  setCommandPaletteOpen: (v: boolean) => void;
  toggleCommandPalette: () => void;
  setActiveWorkloadTab: (tab: string) => void;
  triggerAction: (action: string, modelId?: string) => void;
}

const Ctx = createContext<ModelsStoreCtx | null>(null);

export const ModelsStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [models] = useState<RegistryModel[]>(MOCK_MODELS);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<ModelStatus | 'all'>('all');
  const [providerFilter, setProviderFilter] = useState('all');
  const [selectedModel, setSelectedModel] = useState<RegistryModel | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTab, setDrawerTab] = useState('overview');
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [activeWorkloadTab, setActiveWorkloadTab] = useState('coding');

  const openDrawer = useCallback((model: RegistryModel, tab = 'overview') => {
    setSelectedModel(model);
    setDrawerTab(tab);
    setDrawerOpen(true);
  }, []);

  const closeDrawer = useCallback(() => {
    setDrawerOpen(false);
    setTimeout(() => setSelectedModel(null), 300);
  }, []);

  const toggleCompare = useCallback((id: string) => {
    setCompareIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : prev.length < 4 ? [...prev, id] : prev,
    );
  }, []);

  const clearCompare = useCallback(() => setCompareIds([]), []);

  const toggleCommandPalette = useCallback(() => {
    setCommandPaletteOpen((prev) => !prev);
  }, []);

  const triggerAction = useCallback((action: string, modelId?: string) => {
    const target = modelId ? models.find((m) => m.id === modelId) : selectedModel || models[0];
    if (target) {
      if (action === 'telemetry' || action === 'inspect') openDrawer(target, 'metrics');
      else if (action === 'logs') openDrawer(target, 'logs');
      else openDrawer(target, 'overview');
    }
  }, [models, selectedModel, openDrawer]);

  const value = useMemo(() => ({
    models, search, statusFilter, providerFilter,
    selectedModel, drawerOpen, drawerTab, compareIds,
    commandPaletteOpen, activeWorkloadTab,
    setSearch, setStatusFilter, setProviderFilter,
    openDrawer, closeDrawer, setDrawerTab, toggleCompare, clearCompare,
    setCommandPaletteOpen, toggleCommandPalette, setActiveWorkloadTab, triggerAction,
  }), [
    models, search, statusFilter, providerFilter,
    selectedModel, drawerOpen, drawerTab, compareIds,
    commandPaletteOpen, activeWorkloadTab,
    openDrawer, closeDrawer, toggleCompare, clearCompare,
    toggleCommandPalette, triggerAction
  ]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
};

export const useModelsStore = () => {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useModelsStore must be inside ModelsStoreProvider');
  return ctx;
};
