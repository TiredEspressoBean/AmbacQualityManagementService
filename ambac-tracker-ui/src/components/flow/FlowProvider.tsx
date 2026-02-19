import {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  type ReactNode,
} from 'react';
import { useReactFlow } from '@xyflow/react';
import type {
  FlowMode,
  FlowConfig,
  FlowContextValue,
  FlowNodeData,
  StepData,
} from './types';
import { MODE_CONFIGS as defaultConfigs } from './types';

// ============================================================================
// Context
// ============================================================================

const FlowContext = createContext<FlowContextValue | null>(null);

/**
 * Hook to access flow context. Must be used within FlowProvider.
 */
export function useFlowContext(): FlowContextValue {
  const context = useContext(FlowContext);
  if (!context) {
    throw new Error('useFlowContext must be used within a FlowProvider');
  }
  return context;
}

/**
 * Hook to access flow context, returns null if not in provider.
 * Useful for components that may or may not be in a flow context.
 */
export function useFlowContextSafe(): FlowContextValue | null {
  return useContext(FlowContext);
}

// ============================================================================
// Provider Props
// ============================================================================

export interface FlowProviderProps {
  children: ReactNode;
  /** Flow mode determines behavior and available features */
  mode: FlowMode;
  /** Override default config for the mode */
  configOverrides?: Partial<FlowConfig>;
  /** Initial edit mode state (only for template mode) */
  initialEditMode?: boolean;
  /** Callback when a step is updated */
  onNodeUpdate?: (nodeId: string, data: Partial<StepData>) => void;
  /** Callback when flow is saved */
  onSave?: () => void;
}

// ============================================================================
// Internal Provider (must be inside ReactFlowProvider)
// ============================================================================

function FlowProviderInner({
  children,
  mode,
  configOverrides,
  initialEditMode = false,
  onNodeUpdate,
  onSave,
}: FlowProviderProps) {
  const { getNode } = useReactFlow();

  // Selected node state
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Edit mode state (only relevant for template mode)
  const [isEditMode, setIsEditMode] = useState(initialEditMode);

  // Merge default config with overrides
  const config = useMemo<FlowConfig>(() => ({
    ...defaultConfigs[mode],
    ...configOverrides,
  }), [mode, configOverrides]);

  // Get selected node data
  const selectedNodeData = useMemo<FlowNodeData | null>(() => {
    if (!selectedNodeId) return null;
    const node = getNode(selectedNodeId);
    return node?.data as FlowNodeData | null;
  }, [selectedNodeId, getNode]);

  // Select node handler
  const selectNode = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId);
  }, []);

  // Edit mode handler (only allow in template mode)
  const handleSetEditMode = useCallback((enabled: boolean) => {
    if (mode === 'template') {
      setIsEditMode(enabled);
    }
  }, [mode]);

  const value = useMemo<FlowContextValue>(() => ({
    mode,
    config,
    selectedNodeId,
    selectNode,
    selectedNodeData,
    isEditMode: mode === 'template' ? isEditMode : false,
    setEditMode: handleSetEditMode,
    onNodeUpdate,
    onSave,
  }), [
    mode,
    config,
    selectedNodeId,
    selectNode,
    selectedNodeData,
    isEditMode,
    handleSetEditMode,
    onNodeUpdate,
    onSave,
  ]);

  return (
    <FlowContext.Provider value={value}>
      {children}
    </FlowContext.Provider>
  );
}

// ============================================================================
// Public Provider
// ============================================================================

/**
 * FlowProvider must be used inside ReactFlowProvider.
 * It provides mode-specific configuration and state management.
 *
 * @example
 * ```tsx
 * <ReactFlowProvider>
 *   <FlowProvider mode="template" onSave={handleSave}>
 *     <FlowCanvas nodes={nodes} edges={edges} />
 *     <StepEditorPanel />
 *   </FlowProvider>
 * </ReactFlowProvider>
 * ```
 */
export function FlowProvider(props: FlowProviderProps) {
  return <FlowProviderInner {...props} />;
}

// ============================================================================
// Utility Hooks
// ============================================================================

/**
 * Hook to check if current mode allows editing.
 */
export function useCanEdit(): boolean {
  const { config, isEditMode } = useFlowContext();
  return config.editable && isEditMode;
}

/**
 * Hook to get overlay configuration for current mode.
 */
export function useOverlays() {
  const { config } = useFlowContext();
  return config.overlays;
}

/**
 * Hook to get panel type for current mode.
 */
export function usePanelType() {
  const { config } = useFlowContext();
  return config.panelType;
}

/**
 * Hook for node selection with automatic panel display.
 */
export function useNodeSelection() {
  const { selectedNodeId, selectNode, selectedNodeData, config } = useFlowContext();

  const handleNodeClick = useCallback((nodeId: string) => {
    if (config.selectable) {
      selectNode(nodeId);
    }
  }, [config.selectable, selectNode]);

  const clearSelection = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  return {
    selectedNodeId,
    selectedNodeData,
    handleNodeClick,
    clearSelection,
    hasSelection: selectedNodeId !== null,
  };
}
