import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRetrieveProcessWithSteps } from '@/hooks/useRetrieveProcessWithSteps';
import type {
  FlowData,
  FlowNode,
  FlowEdge,
  StepData,
  StepType,
  FlowNodeData,
  NodeMetrics,
  ProcessStepData,
  StepEdgeData,
  StepWithOrder,
  DecisionType,
  EdgeType,
  TerminalStatus,
} from '../types';

interface UseProcessMetricsFlowParams {
  processId: string | null;
  /** Date range for metrics calculation */
  dateRange?: {
    start: Date;
    end: Date;
  };
  enabled?: boolean;
}

interface StepMetricsResponse {
  step_id: string | number;
  avg_dwell_time_ms: number;
  avg_transition_time_ms: number;
  throughput_per_hour: number;
  pass_rate: number | null;
  rework_rate: number | null;
  total_parts: number;
}

/**
 * Determine node type for a step.
 */
function getNodeType(step: StepData, isEntryPoint: boolean): StepType {
  if (step.step_type && step.step_type !== 'task') return step.step_type;
  if (step.is_terminal) return 'terminal';
  if (step.is_decision_point) return 'decision';
  if (isEntryPoint) return 'start';
  if (step.max_visits) return 'rework';
  if (step.expected_duration) return 'timer';
  return 'task';
}

/**
 * Calculate bottleneck severity (0-1) based on metrics.
 * Higher severity = worse bottleneck.
 */
function calculateBottleneckSeverity(
  metrics: NodeMetrics,
  allMetrics: NodeMetrics[]
): number {
  if (allMetrics.length === 0) return 0;

  // Find max dwell time across all steps
  const maxDwellTime = Math.max(...allMetrics.map((m) => m.avgDwellTime));
  if (maxDwellTime === 0) return 0;

  // Severity based on relative dwell time
  const dwellRatio = metrics.avgDwellTime / maxDwellTime;

  // Adjust for low throughput
  const avgThroughput = allMetrics.reduce((sum, m) => sum + m.throughput, 0) / allMetrics.length;
  const throughputFactor = avgThroughput > 0 ? Math.max(0, 1 - metrics.throughput / avgThroughput) : 0;

  // Combined severity (weighted)
  return Math.min(1, dwellRatio * 0.7 + throughputFactor * 0.3);
}

/**
 * Transform process_steps, step_edges, and metrics to flow with bottleneck indicators.
 */
function transformToMetricsFlow(
  processSteps: ProcessStepData[],
  stepEdges: StepEdgeData[],
  metricsMap: Map<string, NodeMetrics>,
  processName?: string
): FlowData {
  if (!processSteps || processSteps.length === 0) {
    return { nodes: [], edges: [], meta: { title: processName } };
  }

  const nodes: FlowNode[] = [];
  const edges: FlowEdge[] = [];

  // Sort by order
  const sortedProcessSteps = [...processSteps].sort((a, b) => a.order - b.order);

  // Get all metrics for severity calculation
  const allMetrics = Array.from(metricsMap.values());

  // Find which steps are targets of edges
  const targetStepIds = new Set<string>();
  stepEdges.forEach((edge) => {
    targetStepIds.add(edge.to_step);
  });

  // Create nodes with metrics
  sortedProcessSteps.forEach((ps, index) => {
    const step = ps.step;
    const isEntryPoint = ps.is_entry_point || (!targetStepIds.has(step.id) && index === 0);
    const nodeType = getNodeType(step, isEntryPoint);
    const metrics = metricsMap.get(step.id);
    const bottleneckSeverity = metrics
      ? calculateBottleneckSeverity(metrics, allMetrics)
      : 0;

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
      highlighted: bottleneckSeverity >= 0.6,
      overlays: {
        metrics,
        isBottleneck: bottleneckSeverity >= 0.6,
      },
    };

    nodes.push({
      id: String(step.id),
      type: nodeType,
      position: { x: index * 250, y: 0 },
      data: nodeData,
      // Apply visual styling for bottlenecks
      className: bottleneckSeverity >= 0.8
        ? 'shadow-red-500/50 shadow-xl'
        : bottleneckSeverity >= 0.6
          ? 'shadow-orange-500/40 shadow-lg'
          : undefined,
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
      title: `${processName} - Performance Analysis`,
    },
  };
}

/**
 * Adapter hook for process metrics/evaluation flow.
 * Shows process with bottleneck indicators and performance metrics.
 *
 * NOTE: This requires a backend endpoint to fetch metrics.
 * Until that's implemented, it will use mock data.
 */
export function useProcessMetricsFlow({
  processId,
  dateRange,
  enabled = true,
}: UseProcessMetricsFlowParams) {
  // Fetch process with steps
  const {
    data: process,
    isLoading: isLoadingProcess,
    error: processError,
  } = useRetrieveProcessWithSteps(
    { params: { id: processId ?? '' } },
    { enabled: enabled && processId !== null }
  );

  // Fetch metrics (placeholder - endpoint doesn't exist yet)
  // TODO: Replace with actual API call when endpoint is created
  const {
    data: metricsData,
    isLoading: isLoadingMetrics,
    error: metricsError,
  } = useQuery({
    queryKey: ['process-metrics', processId, dateRange, process?.process_steps],
    queryFn: async (): Promise<StepMetricsResponse[]> => {
      // Placeholder: Return mock data until API is implemented
      // In production, this would be:
      // return api.api_Processes_metrics_retrieve({ params: { id: processId }, queries: dateRange });

      if (!process?.process_steps) return [];

      // Generate mock metrics for demo
      return process.process_steps.map((ps) => ({
        step_id: ps.step.id,
        avg_dwell_time_ms: Math.random() * 3600000 * 4, // 0-4 hours
        avg_transition_time_ms: Math.random() * 300000, // 0-5 minutes
        throughput_per_hour: Math.random() * 20 + 2, // 2-22/hr
        pass_rate: ps.step.is_terminal ? null : Math.random() * 20 + 80, // 80-100%
        rework_rate: Math.random() * 10, // 0-10%
        total_parts: Math.floor(Math.random() * 500 + 100),
      }));
    },
    enabled: enabled && processId !== null && !!process,
  });

  // Transform metrics to map
  const metricsMap = useMemo(() => {
    const map = new Map<string, NodeMetrics>();
    if (metricsData) {
      metricsData.forEach((m) => {
        map.set(String(m.step_id), {
          avgDwellTime: m.avg_dwell_time_ms,
          avgTransitionTime: m.avg_transition_time_ms,
          throughput: m.throughput_per_hour,
          passRate: m.pass_rate ?? undefined,
          reworkRate: m.rework_rate ?? undefined,
          totalParts: m.total_parts,
        });
      });
    }
    return map;
  }, [metricsData]);

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

    return transformToMetricsFlow(processSteps, stepEdges, metricsMap, process.name);
  }, [process, metricsMap]);

  return {
    data: flowData,
    isLoading: isLoadingProcess || isLoadingMetrics,
    error: (processError || metricsError) as Error | null,
    process,
    metricsMap,
  };
}
