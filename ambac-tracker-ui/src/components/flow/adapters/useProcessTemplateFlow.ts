import { useMemo } from 'react';
import { useRetrieveProcessWithSteps } from '@/hooks/useRetrieveProcessWithSteps';
import type {
  FlowData,
  FlowNode,
  FlowEdge,
  StepData,
  StepType,
  FlowNodeData,
  ProcessStepData,
  StepEdgeData,
  StepWithOrder,
  DecisionType,
  EdgeType,
  TerminalStatus,
} from '../types';

interface UseProcessTemplateFlowParams {
  processId: string | null;
  enabled?: boolean;
}

/**
 * Determine the node type for a step.
 * Uses explicit step_type if set, otherwise derives from properties.
 */
function getNodeType(step: StepData, isEntryPoint: boolean): StepType {
  // Use explicit step_type if set (and not default 'task')
  if (step.step_type && step.step_type !== 'task') {
    return step.step_type;
  }

  // Derive from properties
  if (step.is_terminal) return 'terminal';
  if (step.is_decision_point) return 'decision';
  if (isEntryPoint) return 'start';
  if (step.max_visits) return 'rework';
  if (step.expected_duration) return 'timer';

  return 'task';
}

/**
 * Transform process_steps and step_edges to flow nodes and edges.
 */
function transformToFlow(
  processSteps: ProcessStepData[],
  stepEdges: StepEdgeData[],
  processName?: string
): FlowData {
  if (!processSteps || processSteps.length === 0) {
    return { nodes: [], edges: [], meta: { title: processName } };
  }

  const nodes: FlowNode[] = [];
  const edges: FlowEdge[] = [];

  // Sort by order
  const sortedProcessSteps = [...processSteps].sort((a, b) => a.order - b.order);

  // Find which steps are targets of edges (to help identify start nodes if is_entry_point not set)
  const targetStepIds = new Set<string>();
  stepEdges.forEach((edge) => {
    targetStepIds.add(edge.to_step);
  });

  // Create nodes from ProcessSteps
  sortedProcessSteps.forEach((ps, index) => {
    const step = ps.step;
    const isEntryPoint = ps.is_entry_point || (!targetStepIds.has(step.id) && index === 0);
    const nodeType = getNodeType(step, isEntryPoint);

    // Create StepWithOrder for node data
    const stepWithOrder: StepWithOrder = {
      ...step,
      order: ps.order,
      is_entry_point: ps.is_entry_point,
    };

    const nodeData: FlowNodeData = {
      label: step.name,
      description: step.description,
      step: stepWithOrder,
      stepType: nodeType,
      isDecisionPoint: step.is_decision_point,
      decisionType: step.decision_type,
      isTerminal: step.is_terminal,
      terminalStatus: step.terminal_status,
      maxVisits: step.max_visits ?? undefined,
      expectedDuration: step.expected_duration ?? undefined,
      isStart: isEntryPoint,
      overlays: {
        qaRequired: step.requires_qa_signoff,
        samplingRate: step.min_sampling_rate,
      },
    };

    nodes.push({
      id: String(step.id),
      type: nodeType,
      position: { x: index * 250, y: 0 }, // Initial position, will be layouted
      data: nodeData,
    });
  });

  // Create edges from StepEdges
  if (stepEdges.length > 0) {
    stepEdges.forEach((edge) => {
      const sourceStep = sortedProcessSteps.find(ps => ps.step.id === edge.from_step)?.step;

      if (edge.edge_type === 'default') {
        edges.push({
          id: `e${edge.from_step}-${edge.to_step}`,
          source: String(edge.from_step),
          target: String(edge.to_step),
          label: sourceStep?.is_decision_point ? 'Pass' : undefined,
          type: 'smoothstep',
          style: { stroke: sourceStep?.is_decision_point ? '#10b981' : undefined },
          animated: sourceStep?.is_decision_point,
        });
      } else if (edge.edge_type === 'alternate') {
        edges.push({
          id: `e${edge.from_step}-${edge.to_step}-alt`,
          source: String(edge.from_step),
          target: String(edge.to_step),
          label: 'Fail',
          type: 'smoothstep',
          style: { stroke: '#ef4444' },
          animated: true,
        });
      } else if (edge.edge_type === 'escalation') {
        edges.push({
          id: `e${edge.from_step}-${edge.to_step}-esc`,
          source: String(edge.from_step),
          target: String(edge.to_step),
          label: 'Max Exceeded',
          type: 'smoothstep',
          style: { stroke: '#f97316', strokeDasharray: '5,5' },
          animated: true,
        });
      }
    });
  } else {
    // Fallback: auto-connect steps by order if no edges defined
    sortedProcessSteps.forEach((ps, index) => {
      if (index < sortedProcessSteps.length - 1 && !ps.step.is_terminal) {
        const nextPs = sortedProcessSteps[index + 1];
        edges.push({
          id: `e${ps.step.id}-${nextPs.step.id}`,
          source: String(ps.step.id),
          target: String(nextPs.step.id),
          type: 'smoothstep',
        });
      }
    });
  }

  return {
    nodes,
    edges,
    meta: {
      title: processName,
    },
  };
}

/**
 * Adapter hook for process template flow.
 * Fetches process with steps and transforms to FlowData.
 */
export function useProcessTemplateFlow({ processId, enabled = true }: UseProcessTemplateFlowParams) {
  const {
    data: process,
    isLoading,
    error,
    refetch,
  } = useRetrieveProcessWithSteps(
    { params: { id: processId ?? '' } },
    { enabled: enabled && processId !== null }
  );

  const flowData = useMemo<FlowData | null>(() => {
    if (!process) return null;

    // Transform process_steps and step_edges to flow data
    const processSteps: ProcessStepData[] = (process.process_steps || []).map((ps) => ({
      id: String(ps.id),
      order: ps.order,
      is_entry_point: ps.is_entry_point,
      step: {
        id: String(ps.step.id),
        name: ps.step.name,
        description: ps.step.description ?? undefined,
        step_type: ps.step.step_type as StepType | undefined,
        is_decision_point: ps.step.is_decision_point,
        decision_type: ps.step.decision_type as DecisionType | undefined,
        is_terminal: ps.step.is_terminal,
        terminal_status: ps.step.terminal_status as TerminalStatus | undefined,
        max_visits: ps.step.max_visits,
        expected_duration: ps.step.expected_duration,
        requires_qa_signoff: ps.step.requires_qa_signoff,
        sampling_required: ps.step.sampling_required,
        min_sampling_rate: ps.step.min_sampling_rate,
        block_on_quarantine: ps.step.block_on_quarantine,
        pass_threshold: ps.step.pass_threshold,
        part_type: ps.step.part_type ? String(ps.step.part_type) : undefined,
        part_type_name: ps.step.part_type_name,
      },
    }));

    const stepEdges: StepEdgeData[] = (process.step_edges || []).map((e) => ({
      id: String(e.id),
      from_step: String(e.from_step),
      to_step: String(e.to_step),
      edge_type: (e.edge_type || 'default') as EdgeType,
      from_step_name: e.from_step_name,
      to_step_name: e.to_step_name,
      condition_measurement: e.condition_measurement,
      condition_operator: e.condition_operator as StepEdgeData['condition_operator'],
      condition_value: e.condition_value,
    }));

    return transformToFlow(processSteps, stepEdges, process.name);
  }, [process]);

  return {
    data: flowData,
    isLoading,
    error: error as Error | null,
    refetch,
    // Also expose the raw process for metadata
    process,
  };
}
