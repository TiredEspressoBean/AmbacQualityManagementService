import { useMemo } from 'react';
import { useRetrieveWorkOrder } from '@/hooks/useRetrieveWorkOrder';
import { useRetrieveProcessWithSteps } from '@/hooks/useRetrieveProcessWithSteps';
import { useRetrieveParts } from '@/hooks/useRetrieveParts';
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

interface UseWorkOrderFlowParams {
  workOrderId: string | null;
  enabled?: boolean;
}

/**
 * Determine the node type for a step.
 */
function getNodeType(step: StepData, isEntryPoint: boolean): StepType {
  if (step.step_type && step.step_type !== 'task') {
    return step.step_type;
  }
  if (step.is_terminal) return 'terminal';
  if (step.is_decision_point) return 'decision';
  if (isEntryPoint) return 'start';
  if (step.max_visits) return 'rework';
  if (step.expected_duration) return 'timer';
  return 'task';
}

/**
 * Transform process_steps, step_edges, and parts data to flow with part counts.
 */
function transformToWorkOrderFlow(
  processSteps: ProcessStepData[],
  stepEdges: StepEdgeData[],
  partsByStep: Map<string, number>,
  workOrderName?: string,
  processName?: string
): FlowData {
  if (!processSteps || processSteps.length === 0) {
    return { nodes: [], edges: [], meta: { title: workOrderName } };
  }

  const nodes: FlowNode[] = [];
  const edges: FlowEdge[] = [];

  // Sort by order
  const sortedProcessSteps = [...processSteps].sort((a, b) => a.order - b.order);

  // Find which steps are targets of edges
  const targetStepIds = new Set<string>();
  stepEdges.forEach((edge) => {
    targetStepIds.add(edge.to_step);
  });

  // Create nodes with part counts
  sortedProcessSteps.forEach((ps, index) => {
    const step = ps.step;
    const isEntryPoint = ps.is_entry_point || (!targetStepIds.has(step.id) && index === 0);
    const nodeType = getNodeType(step, isEntryPoint);
    const partCount = partsByStep.get(step.id) || 0;

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
      highlighted: partCount > 0,
      overlays: {
        partCount,
        qaRequired: step.requires_qa_signoff,
        samplingRate: step.min_sampling_rate,
      },
    };

    nodes.push({
      id: String(step.id),
      type: nodeType,
      position: { x: index * 250, y: 0 },
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
      title: workOrderName,
      subtitle: processName,
    },
  };
}

/**
 * Adapter hook for work order flow view.
 * Shows process steps with part counts at each step.
 */
export function useWorkOrderFlow({ workOrderId, enabled = true }: UseWorkOrderFlowParams) {
  // Fetch work order
  const {
    data: workOrder,
    isLoading: isLoadingWorkOrder,
    error: workOrderError,
  } = useRetrieveWorkOrder(workOrderId ?? '', { enabled: enabled && workOrderId !== null });

  // Get process ID from work order's order
  const processId = (workOrder as unknown as { order?: { process?: string | number } })?.order?.process;

  // Fetch process with steps
  const {
    data: process,
    isLoading: isLoadingProcess,
    error: processError,
  } = useRetrieveProcessWithSteps(
    { params: { id: processId ? String(processId) : '' } },
    { enabled: enabled && processId !== undefined && processId !== null }
  );

  // Fetch parts for this work order
  const {
    data: partsData,
    isLoading: isLoadingParts,
    error: partsError,
  } = useRetrieveParts(
    { work_order: workOrderId ?? undefined },
    { enabled: enabled && workOrderId !== null }
  );

  // Calculate part counts per step
  const partsByStep = useMemo(() => {
    const counts = new Map<string, number>();
    if (partsData?.results) {
      partsData.results.forEach((part) => {
        const stepId = (part as unknown as { step?: string | number }).step;
        if (stepId) {
          const stepKey = String(stepId);
          counts.set(stepKey, (counts.get(stepKey) || 0) + 1);
        }
      });
    }
    return counts;
  }, [partsData]);

  // Transform to flow data
  const flowData = useMemo<FlowData | null>(() => {
    if (!process) return null;

    // Transform process_steps
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
      },
    }));

    // Transform step_edges
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

    const workOrderName = (workOrder as unknown as { name?: string })?.name ?? `Work Order #${workOrderId}`;

    return transformToWorkOrderFlow(processSteps, stepEdges, partsByStep, workOrderName, process.name);
  }, [process, partsByStep, workOrder, workOrderId]);

  return {
    data: flowData,
    isLoading: isLoadingWorkOrder || isLoadingProcess || isLoadingParts,
    error: (workOrderError || processError || partsError) as Error | null,
    workOrder,
    process,
    partsByStep,
  };
}
