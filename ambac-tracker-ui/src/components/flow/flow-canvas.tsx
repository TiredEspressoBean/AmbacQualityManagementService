import { useCallback, useMemo, useEffect, useLayoutEffect, useRef } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  addEdge,
  useReactFlow,
  type Node,
  type Edge,
  type Connection,
  type OnConnect,
} from '@xyflow/react';
import { flowNodeTypes } from './nodes';
import { buildNodesAndEdges, useAutoLayout, type StepData } from './use-steps-to-flow';
import type { DemoMode } from '@/lib/demo-data/process-flow-demo';
import { Button } from '@/components/ui/button';
import { Maximize2 } from 'lucide-react';

/** MiniMap color based on node type */
function getNodeColor(node: Node): string {
  switch (node.type) {
    case 'start': return '#22c55e';      // green
    case 'decision': return '#f59e0b';   // amber
    case 'terminal': return '#10b981';   // emerald
    case 'rework': return '#f97316';     // orange
    case 'timer': return '#3b82f6';      // blue
    default: return '#6366f1';           // indigo
  }
}

/** Node types that have pass/fail handles */
const DECISION_NODE_TYPES = new Set(['decision']);

/**
 * Validate edges against nodes to ensure all handle references are valid.
 * Returns edges with corrected handle references.
 *
 * - Decision nodes ONLY have named handles ("pass", "fail") - no default handle
 * - Other nodes ONLY have a default handle (no id) - no named handles
 */
function validateEdges(edges: Edge[], nodes: Node[]): Edge[] {
  const nodeMap = new Map(nodes.map(n => [n.id, n]));

  return edges.map(edge => {
    const sourceNode = nodeMap.get(edge.source);
    if (!sourceNode) return edge; // Source node doesn't exist, leave as-is

    const isDecisionNode = DECISION_NODE_TYPES.has(sourceNode.type || 'task');

    if (isDecisionNode) {
      // Decision nodes only have "pass" and "fail" handles - no default
      // If edge has no sourceHandle or an invalid one, default to "pass"
      if (!edge.sourceHandle || (edge.sourceHandle !== 'pass' && edge.sourceHandle !== 'fail')) {
        return { ...edge, sourceHandle: 'pass' };
      }
    } else {
      // Non-decision nodes only have a default handle (no id)
      // If edge has a sourceHandle, remove it
      if (edge.sourceHandle) {
        return { ...edge, sourceHandle: undefined };
      }
    }

    return edge;
  });
}

export interface FlowCanvasProps {
  steps: StepData[];
  /** Step edges from API - if provided, used for routing instead of auto-connect by order */
  stepEdges?: Array<{ from_step: number; to_step: number; edge_type: string }>;
  selectedNode?: Node | null;
  onNodeClick?: (event: React.MouseEvent, node: Node) => void;
  onPaneClick?: () => void;
  onNodesChange?: (nodes: Node[]) => void;
  onEdgesChange?: (edges: Edge[]) => void;
  editable?: boolean;
  /** Demo mode for overlay rendering */
  demoMode?: DemoMode;
  /** Callback when delete key is pressed on a selected node */
  onDeleteNode?: (nodeId: string) => void;
}

/** Handle type for imperative methods */
export interface FlowCanvasHandle {
  fitView: () => void;
}

/** Flow canvas component - must be used inside ReactFlowProvider */
export function FlowCanvas({
  steps,
  stepEdges,
  selectedNode,
  onNodeClick,
  onPaneClick,
  onNodesChange: onNodesChangeCallback,
  onEdgesChange: onEdgesChangeCallback,
  editable = false,
  demoMode,
  onDeleteNode,
}: FlowCanvasProps) {
  const { fitView } = useReactFlow();

  // Build initial nodes and edges from steps
  // Convert stepEdges to the format expected by buildNodesAndEdges (memoized)
  const edgeInputs = useMemo(() =>
    stepEdges?.map(e => ({
      from_step: e.from_step,
      to_step: e.to_step,
      edge_type: e.edge_type as 'default' | 'alternate' | 'escalation',
    })),
    [stepEdges]
  );
  // Build nodes and edges from steps - this is the source of truth
  const { nodes: computedNodes, edges: computedEdges } = useMemo(() => {
    const { nodes: newNodes, edges: newEdges } = buildNodesAndEdges(steps, edgeInputs);
    // Add demoMode to each node's data and set connectable based on editable
    // Dragging is always allowed for rearranging the view
    const nodesWithMode = newNodes.map((node) => ({
      ...node,
      draggable: true,
      connectable: editable,
      data: {
        ...node.data,
        demoMode,
      },
    }));
    return { nodes: nodesWithMode, edges: newEdges };
  }, [steps, edgeInputs, demoMode, editable]);

  const [nodes, setNodes, onNodesChange] = useNodesState(computedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(computedEdges);

  // Auto-layout after nodes are measured
  const { resetLayout } = useAutoLayout({ direction: 'RIGHT', nodeSpacing: 50, layerSpacing: 120 });

  // Track the last synced values to detect when we need to force a sync
  const lastSyncedStepsRef = useRef(steps);
  const lastSyncedEdgeInputsRef = useRef(edgeInputs);
  const lastSyncedEditableRef = useRef(editable);

  // Sync nodes/edges when steps, edges, or editable change - use layoutEffect to run before paint
  // This prevents React Flow from rendering with stale edges that reference non-existent handles
  useLayoutEffect(() => {
    // Only sync if the source data has actually changed
    const stepsChanged = lastSyncedStepsRef.current !== steps;
    const edgesChanged = lastSyncedEdgeInputsRef.current !== edgeInputs;
    const editableChanged = lastSyncedEditableRef.current !== editable;

    if (stepsChanged || edgesChanged || editableChanged) {
      setNodes(computedNodes);
      setEdges(computedEdges);
      lastSyncedStepsRef.current = steps;
      lastSyncedEdgeInputsRef.current = edgeInputs;
      lastSyncedEditableRef.current = editable;
      // Only reset layout when steps/edges change, not when just editable changes
      if (stepsChanged || edgesChanged) {
        resetLayout();
      }
    }
  }, [steps, edgeInputs, editable, computedNodes, computedEdges, setNodes, setEdges, resetLayout]);

  // Notify parent of changes
  useEffect(() => {
    onNodesChangeCallback?.(nodes);
  }, [nodes, onNodesChangeCallback]);

  useEffect(() => {
    onEdgesChangeCallback?.(edges);
  }, [edges, onEdgesChangeCallback]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Delete key - remove selected node
      if ((event.key === 'Delete' || event.key === 'Backspace') && selectedNode && editable) {
        event.preventDefault();
        onDeleteNode?.(selectedNode.id);
      }
      // Escape - deselect
      if (event.key === 'Escape' && selectedNode) {
        event.preventDefault();
        onPaneClick?.();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedNode, editable, onDeleteNode, onPaneClick]);

  // Handle new connections
  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (!editable) return;
      setEdges((eds) => addEdge({
        ...connection,
        type: 'smoothstep',
        animated: true,
      }, eds));
    },
    [setEdges, editable]
  );

  const handleFitView = useCallback(() => {
    fitView({ padding: 0.1, maxZoom: 1, duration: 200 });
  }, [fitView]);

  // Validate edges against current nodes to prevent handle mismatch errors
  // This catches cases where edges have stale handle references that don't match node types
  const validatedEdges = useMemo(() => validateEdges(edges, nodes), [edges, nodes]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={validatedEdges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={onNodeClick}
      onPaneClick={onPaneClick}
      onConnect={onConnect}
      nodeTypes={flowNodeTypes}
      fitView
      minZoom={0.1}
      maxZoom={2}
      defaultEdgeOptions={{ type: 'smoothstep', animated: true }}
      nodesDraggable={true}
      nodesConnectable={editable}
      edgesUpdatable={editable}
      elementsSelectable={true}
      selectNodesOnDrag={false}
      deleteKeyCode={editable ? 'Delete' : null}
    >
      <Controls position="top-left" />
      <MiniMap
        nodeColor={getNodeColor}
        zoomable
        pannable
        position="bottom-left"
      />
      <Background variant={BackgroundVariant.Dots} gap={16} size={1} />

      {/* Fit View Button */}
      <div className="absolute top-2 right-2 z-10">
        <Button
          variant="outline"
          size="sm"
          onClick={handleFitView}
          className="bg-background/80 backdrop-blur-sm"
        >
          <Maximize2 className="h-4 w-4 mr-1" />
          Fit
        </Button>
      </div>
    </ReactFlow>
  );
}
