import type { Node, Edge } from '@xyflow/react';

// ============================================================================
// Flow Modes
// ============================================================================

/**
 * The different contexts/modes the flow editor can operate in.
 */
export type FlowMode =
  | 'template'        // Edit process definition
  | 'workorder'       // View parts at each step in a work order
  | 'part-journey'    // Track single part's execution path
  | 'evaluation'      // Bottleneck analysis with metrics
  | 'capa'            // CAPA workflow visualization
  | 'approval'        // Document approval flow
  | 'qa-checkpoints'  // QA inspection points overlay
  | 'ncr'             // Non-conformance flow
  | 'disposition';    // Disposition decision tree

/**
 * Configuration for flow behavior based on mode.
 */
export interface FlowConfig {
  /** Whether nodes/edges can be modified */
  editable: boolean;
  /** Whether nodes can be selected */
  selectable: boolean;
  /** Whether the flow can be panned/zoomed */
  interactive: boolean;
  /** Show minimap */
  showMinimap: boolean;
  /** Show controls (zoom, fit) */
  showControls: boolean;
  /** Show background grid */
  showBackground: boolean;
  /** Which overlays to display */
  overlays: OverlayType[];
  /** Panel type to show on node selection */
  panelType: PanelType | null;
}

/**
 * Default configurations per mode.
 */
export const MODE_CONFIGS: Record<FlowMode, FlowConfig> = {
  template: {
    editable: true,
    selectable: true,
    interactive: true,
    showMinimap: true,
    showControls: true,
    showBackground: true,
    overlays: [],
    panelType: 'step-editor',
  },
  workorder: {
    editable: false,
    selectable: true,
    interactive: true,
    showMinimap: true,
    showControls: true,
    showBackground: false,
    overlays: ['part-count', 'progress'],
    panelType: 'part-list',
  },
  'part-journey': {
    editable: false,
    selectable: true,
    interactive: true,
    showMinimap: false,
    showControls: true,
    showBackground: false,
    overlays: ['execution-time', 'visit-count'],
    panelType: 'execution-history',
  },
  evaluation: {
    editable: false,
    selectable: true,
    interactive: true,
    showMinimap: true,
    showControls: true,
    showBackground: false,
    overlays: ['metrics', 'bottleneck'],
    panelType: 'metrics',
  },
  capa: {
    editable: false,
    selectable: true,
    interactive: true,
    showMinimap: false,
    showControls: true,
    showBackground: false,
    overlays: ['status'],
    panelType: 'step-detail',
  },
  approval: {
    editable: false,
    selectable: true,
    interactive: true,
    showMinimap: false,
    showControls: true,
    showBackground: false,
    overlays: ['approval-status'],
    panelType: 'step-detail',
  },
  'qa-checkpoints': {
    editable: false,
    selectable: true,
    interactive: true,
    showMinimap: true,
    showControls: true,
    showBackground: false,
    overlays: ['qa-indicator', 'sampling-rate'],
    panelType: 'step-detail',
  },
  ncr: {
    editable: false,
    selectable: true,
    interactive: true,
    showMinimap: false,
    showControls: true,
    showBackground: false,
    overlays: ['status'],
    panelType: 'step-detail',
  },
  disposition: {
    editable: false,
    selectable: true,
    interactive: true,
    showMinimap: false,
    showControls: true,
    showBackground: false,
    overlays: [],
    panelType: 'step-detail',
  },
};

// ============================================================================
// Overlay Types
// ============================================================================

export type OverlayType =
  | 'part-count'       // Shows number of parts at step
  | 'metrics'          // Shows avg time, throughput
  | 'bottleneck'       // Red glow for slow steps
  | 'visit-count'      // Shows current/max visits for rework
  | 'execution-time'   // Shows time spent at step
  | 'progress'         // Progress ring/bar
  | 'qa-indicator'     // QA checkpoint icon
  | 'sampling-rate'    // Sampling percentage
  | 'status'           // Generic status badge
  | 'approval-status'; // Approval state (pending, approved, rejected)

export type PanelType =
  | 'step-editor'        // Edit step properties
  | 'step-detail'        // View-only step info
  | 'part-list'          // Parts at selected step
  | 'metrics'            // Detailed metrics for step
  | 'execution-history'; // Step execution timeline

// ============================================================================
// Node Data Types
// ============================================================================

/**
 * Base step type - matches backend Steps model.
 */
export type StepType = 'task' | 'start' | 'decision' | 'rework' | 'timer' | 'terminal';

export type TerminalStatus =
  | 'completed'
  | 'shipped'
  | 'stock'
  | 'scrapped'
  | 'returned'
  | 'awaiting_pickup'
  | 'core_banked'
  | 'rma_closed';

export type DecisionType = 'qa_result' | 'measurement' | 'manual';

/**
 * Step data from backend API (node properties only - no routing).
 */
export interface StepData {
  id: string;
  name: string;
  step_type?: StepType;
  is_decision_point?: boolean;
  decision_type?: DecisionType;
  is_terminal?: boolean;
  terminal_status?: TerminalStatus;
  description?: string;
  max_visits?: number | null;
  expected_duration?: string | null;
  part_type?: string;
  part_type_name?: string;
  // QA fields
  requires_qa_signoff?: boolean;
  sampling_required?: boolean;
  min_sampling_rate?: number;
  block_on_quarantine?: boolean;
  pass_threshold?: number;
  revisit_assignment?: 'any' | 'same' | 'different' | 'role';
}

/**
 * ProcessStep junction - links a Step to a Process with ordering.
 */
export interface ProcessStepData {
  id: string;
  step: StepData;
  order: number;
  is_entry_point?: boolean;
}

/**
 * StepEdge - routing between steps in a process.
 */
export type EdgeType = 'default' | 'alternate' | 'escalation';

export interface StepEdgeData {
  id: string;
  from_step: string;
  to_step: string;
  edge_type: EdgeType;
  from_step_name?: string;
  to_step_name?: string;
  condition_measurement?: string | null;
  condition_operator?: 'gte' | 'lte' | 'eq' | '';
  condition_value?: string | null;
}

/**
 * Combined step data with order (for internal use after flattening ProcessStep).
 * Used when transforming API data to flow nodes.
 */
export interface StepWithOrder extends StepData {
  order: number;
  is_entry_point?: boolean;
}

/**
 * Extended node data for flow visualization.
 * Includes step data plus overlay/display data.
 */
export interface FlowNodeData {
  // Allow additional properties for @xyflow/react compatibility
  [key: string]: unknown;
  // Display
  label: string;
  description?: string;
  highlighted?: boolean;

  // Step reference
  step?: StepData;
  stepType: StepType;

  // Decision node fields
  isDecisionPoint?: boolean;
  decisionType?: DecisionType;

  // Terminal node fields
  isTerminal?: boolean;
  terminalStatus?: TerminalStatus;

  // Rework node fields
  maxVisits?: number;
  visitNumber?: number;

  // Timer node fields
  expectedDuration?: string;

  // Start node
  isStart?: boolean;

  // Overlay data (populated by adapters based on mode)
  overlays?: {
    partCount?: number;
    metrics?: NodeMetrics;
    isBottleneck?: boolean;
    executionTime?: number; // milliseconds
    progress?: number; // 0-100
    qaRequired?: boolean;
    samplingRate?: number;
    status?: string;
    approvalStatus?: 'pending' | 'approved' | 'rejected';
  };
}

/**
 * Metrics data for evaluation mode.
 */
export interface NodeMetrics {
  avgDwellTime: number;       // Average time parts spend at this step (ms)
  avgTransitionTime: number;  // Average time to transition to next step (ms)
  throughput: number;         // Parts per hour
  passRate?: number;          // Percentage (0-100)
  reworkRate?: number;        // Percentage (0-100)
  totalParts: number;         // Total parts processed
}

// ============================================================================
// Flow Data (normalized output from adapters)
// ============================================================================

export type FlowNode = Node<FlowNodeData>;
export type FlowEdge = Edge;

/**
 * Normalized flow data returned by all adapters.
 */
export interface FlowData {
  nodes: FlowNode[];
  edges: FlowEdge[];
  /** Optional metadata about the flow */
  meta?: {
    title?: string;
    subtitle?: string;
    processId?: number;
    workOrderId?: number;
    partId?: number;
  };
}

// ============================================================================
// Context Types
// ============================================================================

export interface FlowContextValue {
  /** Current mode */
  mode: FlowMode;
  /** Configuration for current mode */
  config: FlowConfig;
  /** Currently selected node ID */
  selectedNodeId: string | null;
  /** Select a node */
  selectNode: (nodeId: string | null) => void;
  /** Get data for selected node */
  selectedNodeData: FlowNodeData | null;
  /** Whether edit mode is active (only applies to template mode) */
  isEditMode: boolean;
  /** Toggle edit mode */
  setEditMode: (enabled: boolean) => void;
  /** Callback when a node is updated (template mode) */
  onNodeUpdate?: (nodeId: string, data: Partial<StepData>) => void;
  /** Callback when flow is saved (template mode) */
  onSave?: () => void;
}

// ============================================================================
// Adapter Types
// ============================================================================

/**
 * Common interface for flow data adapters.
 * Each adapter fetches data for a specific mode and transforms it to FlowData.
 */
export interface FlowAdapter<TParams = unknown> {
  (params: TParams): {
    data: FlowData | null;
    isLoading: boolean;
    error: Error | null;
    refetch?: () => void;
  };
}

/**
 * Parameters for different adapter types.
 */
export interface ProcessTemplateParams {
  processId: string;
}

export interface WorkOrderFlowParams {
  workOrderId: string;
}

export interface PartJourneyParams {
  partId: string;
}

export interface ProcessEvaluationParams {
  processId: string;
  dateRange?: {
    start: Date;
    end: Date;
  };
}

export interface CapaFlowParams {
  capaId: string;
}

export interface ApprovalFlowParams {
  templateId?: string;
  documentId?: string;
}
