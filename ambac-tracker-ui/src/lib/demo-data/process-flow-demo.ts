import type { StepData, FlowNodeData, NodeMetrics } from '@/components/flow';

/**
 * Demo process data showcasing all node types in a remanufacturing workflow.
 *
 * Flow:
 * Receive Core → Disassemble → Clean (2h) → Inspect ─┬─[Pass]→ Reassemble → Final Test ─┬─[Pass]→ Ship
 *                                                    │                                   │
 *                                                    └─[Fail]─────────┐                  │
 *                                                                     ▼                  │
 *                                                              ┌─► Rework (3 max) ◄──────┘
 *                                                              │      │ [Fail]
 *                                                              │      │
 *                                                              └──────┘
 *                                                                     │
 *                                                               [Max Exceeded]
 *                                                                     │
 *                                                                     ▼
 *                                                             Scrap Decision ─┬─→ Scrap
 *                                                                             └─→ Return to Supplier
 */
export const DEMO_REMANUFACTURING_PROCESS: StepData[] = [
  {
    id: 1,
    name: 'Receive Core',
    order: 1,
    step_type: 'start',
    is_entry_point: true,
    description: 'Receive and log incoming core from customer',
  },
  {
    id: 2,
    name: 'Disassemble',
    order: 2,
    step_type: 'task',
    description: 'Disassemble unit into components',
  },
  {
    id: 3,
    name: 'Clean',
    order: 3,
    step_type: 'timer',
    description: 'Ultrasonic cleaning and degreasing',
    expected_duration: '2h',
  },
  {
    id: 4,
    name: 'Inspect',
    order: 4,
    step_type: 'decision',
    description: 'Visual and dimensional inspection',
    is_decision_point: true,
    decision_type: 'qa_result',
    requires_qa_signoff: true,
    sampling_required: true,
    min_sampling_rate: 100,
  },
  {
    id: 5,
    name: 'Reassemble',
    order: 5,
    step_type: 'task',
    description: 'Reassemble with new seals and gaskets',
  },
  {
    id: 6,
    name: 'Final Test',
    order: 6,
    step_type: 'decision',
    description: 'Pressure test and functional verification',
    is_decision_point: true,
    decision_type: 'measurement',
    requires_qa_signoff: true,
    sampling_required: true,
    min_sampling_rate: 25,
  },
  {
    id: 7,
    name: 'Rework',
    order: 7,
    step_type: 'rework',
    description: 'Address defects found during inspection',
    max_visits: 3,
  },
  {
    id: 8,
    name: 'Scrap Decision',
    order: 8,
    step_type: 'decision',
    description: 'MRB review for unrepairable units',
    is_decision_point: true,
    decision_type: 'manual',
  },
  {
    id: 9,
    name: 'Scrap',
    order: 9,
    step_type: 'terminal',
    description: 'Unit condemned and scrapped',
    is_terminal: true,
    terminal_status: 'scrapped',
  },
  {
    id: 10,
    name: 'Ship',
    order: 10,
    step_type: 'terminal',
    description: 'Package and ship to customer',
    is_terminal: true,
    terminal_status: 'shipped',
  },
  {
    id: 11,
    name: 'Return to Supplier',
    order: 11,
    step_type: 'terminal',
    description: 'Return defective core to supplier',
    is_terminal: true,
    terminal_status: 'returned',
  },
];

/**
 * Demo step edges defining the routing between steps.
 * Matches the flow diagram in the comment above.
 */
export const DEMO_STEP_EDGES: Array<{ from_step: number; to_step: number; edge_type: string }> = [
  // Main flow
  { from_step: 1, to_step: 2, edge_type: 'default' },   // Receive Core → Disassemble
  { from_step: 2, to_step: 3, edge_type: 'default' },   // Disassemble → Clean
  { from_step: 3, to_step: 4, edge_type: 'default' },   // Clean → Inspect
  { from_step: 4, to_step: 5, edge_type: 'default' },   // Inspect → Reassemble (Pass)
  { from_step: 4, to_step: 7, edge_type: 'alternate' }, // Inspect → Rework (Fail)
  { from_step: 5, to_step: 6, edge_type: 'default' },   // Reassemble → Final Test
  { from_step: 6, to_step: 10, edge_type: 'default' },  // Final Test → Ship (Pass)
  { from_step: 6, to_step: 7, edge_type: 'alternate' }, // Final Test → Rework (Fail)
  // Rework loop
  { from_step: 7, to_step: 4, edge_type: 'default' },   // Rework → Inspect (retry)
  { from_step: 7, to_step: 8, edge_type: 'escalation' },// Rework → Scrap Decision (max exceeded)
  // Scrap decision branches
  { from_step: 8, to_step: 9, edge_type: 'default' },   // Scrap Decision → Scrap
  { from_step: 8, to_step: 11, edge_type: 'alternate' },// Scrap Decision → Return to Supplier
];

/** Demo process metadata */
export const DEMO_PROCESS_INFO = {
  id: 'demo',
  name: 'Remanufacturing Process',
  description: 'Demo process showcasing all node types: start, task, timer, decision, rework, and terminal variants',
} as const;

// ============================================================================
// Work Order Progress Demo
// ============================================================================

/**
 * Simulated part distribution across steps for work order demo.
 * Shows how parts are currently distributed in an active work order.
 */
export const DEMO_WORKORDER_PART_COUNTS: Record<number, number> = {
  1: 0,   // Receive Core - none waiting
  2: 2,   // Disassemble - 2 parts
  3: 5,   // Clean - 5 parts (bottleneck!)
  4: 3,   // Inspect - 3 parts
  5: 4,   // Reassemble - 4 parts
  6: 2,   // Final Test - 2 parts
  7: 1,   // Rework - 1 part in rework
  8: 0,   // Scrap Decision - none
  9: 1,   // Scrap - 1 scrapped
  10: 8,  // Ship - 8 shipped
  11: 0,  // Return to Supplier - none
};

export const DEMO_WORKORDER_INFO = {
  id: 'demo-wo',
  name: 'WO-2024-0042',
  description: 'Hydraulic Pump Rebuild - Customer ABC Corp',
  totalParts: 26,
  processName: 'Remanufacturing Process',
} as const;

// ============================================================================
// Part Journey Demo
// ============================================================================

/**
 * Simulated execution history for a single part's journey.
 * Shows the path a part took through the process, including rework loops.
 */
export interface PartExecutionStep {
  stepId: number;
  visitNumber: number;
  entryTime: Date;
  exitTime: Date | null;
  result?: 'pass' | 'fail';
  operator?: string;
}

export const DEMO_PART_JOURNEY: PartExecutionStep[] = [
  { stepId: 1, visitNumber: 1, entryTime: new Date('2024-01-15T08:00:00'), exitTime: new Date('2024-01-15T08:15:00'), operator: 'John D.' },
  { stepId: 2, visitNumber: 1, entryTime: new Date('2024-01-15T08:15:00'), exitTime: new Date('2024-01-15T09:30:00'), operator: 'John D.' },
  { stepId: 3, visitNumber: 1, entryTime: new Date('2024-01-15T09:30:00'), exitTime: new Date('2024-01-15T11:30:00'), operator: 'Auto' },
  { stepId: 4, visitNumber: 1, entryTime: new Date('2024-01-15T11:30:00'), exitTime: new Date('2024-01-15T11:45:00'), result: 'fail', operator: 'Sarah M.' },
  { stepId: 7, visitNumber: 1, entryTime: new Date('2024-01-15T11:45:00'), exitTime: new Date('2024-01-15T13:00:00'), operator: 'Mike R.' },
  { stepId: 4, visitNumber: 2, entryTime: new Date('2024-01-15T13:00:00'), exitTime: new Date('2024-01-15T13:15:00'), result: 'pass', operator: 'Sarah M.' },
  { stepId: 5, visitNumber: 1, entryTime: new Date('2024-01-15T13:15:00'), exitTime: new Date('2024-01-15T14:45:00'), operator: 'John D.' },
  { stepId: 6, visitNumber: 1, entryTime: new Date('2024-01-15T14:45:00'), exitTime: new Date('2024-01-15T15:00:00'), result: 'pass', operator: 'Sarah M.' },
  { stepId: 10, visitNumber: 1, entryTime: new Date('2024-01-15T15:00:00'), exitTime: new Date('2024-01-15T15:30:00'), operator: 'Shipping' },
];

export const DEMO_PART_INFO = {
  id: 'demo-part',
  serialNumber: 'HP-2024-00142',
  partType: 'Hydraulic Pump',
  workOrder: 'WO-2024-0042',
  currentStatus: 'shipped',
} as const;

// ============================================================================
// Process Evaluation / Metrics Demo
// ============================================================================

/**
 * Simulated performance metrics per step for bottleneck analysis.
 */
export const DEMO_STEP_METRICS: Record<number, NodeMetrics> = {
  1: {
    avgDwellTime: 15 * 60 * 1000,        // 15 min
    avgTransitionTime: 2 * 60 * 1000,    // 2 min
    throughput: 24,                       // 24/hr
    totalParts: 500,
  },
  2: {
    avgDwellTime: 75 * 60 * 1000,        // 1h 15m
    avgTransitionTime: 5 * 60 * 1000,
    throughput: 8,
    totalParts: 498,
  },
  3: {
    avgDwellTime: 120 * 60 * 1000,       // 2h (timer step)
    avgTransitionTime: 3 * 60 * 1000,
    throughput: 4,
    totalParts: 496,
  },
  4: {
    avgDwellTime: 45 * 60 * 1000,        // 45 min
    avgTransitionTime: 5 * 60 * 1000,
    throughput: 12,
    passRate: 85,
    totalParts: 580,                      // Higher due to rework revisits
  },
  5: {
    avgDwellTime: 90 * 60 * 1000,        // 1h 30m
    avgTransitionTime: 5 * 60 * 1000,
    throughput: 6,
    totalParts: 493,
  },
  6: {
    avgDwellTime: 30 * 60 * 1000,        // 30 min
    avgTransitionTime: 10 * 60 * 1000,
    throughput: 15,
    passRate: 92,
    totalParts: 493,
  },
  7: {
    avgDwellTime: 180 * 60 * 1000,       // 3h - BOTTLENECK!
    avgTransitionTime: 10 * 60 * 1000,
    throughput: 2.5,
    reworkRate: 100,                      // All parts here are rework
    totalParts: 87,
  },
  8: {
    avgDwellTime: 240 * 60 * 1000,       // 4h - Another bottleneck (MRB review)
    avgTransitionTime: 30 * 60 * 1000,
    throughput: 1,
    totalParts: 12,
  },
  9: {
    avgDwellTime: 15 * 60 * 1000,
    avgTransitionTime: 0,
    throughput: 4,
    totalParts: 7,
  },
  10: {
    avgDwellTime: 30 * 60 * 1000,
    avgTransitionTime: 0,
    throughput: 12,
    totalParts: 481,
  },
  11: {
    avgDwellTime: 60 * 60 * 1000,
    avgTransitionTime: 0,
    throughput: 2,
    totalParts: 5,
  },
};

/**
 * Calculate bottleneck severity (0-1) for a step based on its metrics.
 */
export function calculateBottleneckSeverity(stepId: number): number {
  const metrics = DEMO_STEP_METRICS[stepId];
  if (!metrics) return 0;

  const allMetrics = Object.values(DEMO_STEP_METRICS);
  const maxDwellTime = Math.max(...allMetrics.map(m => m.avgDwellTime));
  const avgThroughput = allMetrics.reduce((sum, m) => sum + m.throughput, 0) / allMetrics.length;

  const dwellRatio = metrics.avgDwellTime / maxDwellTime;
  const throughputFactor = avgThroughput > 0 ? Math.max(0, 1 - metrics.throughput / avgThroughput) : 0;

  return Math.min(1, dwellRatio * 0.7 + throughputFactor * 0.3);
}

// ============================================================================
// QA Checkpoints Demo
// ============================================================================

/**
 * Steps with QA requirements highlighted.
 */
export const DEMO_QA_STEPS = new Set([4, 6]); // Inspect and Final Test

// ============================================================================
// Demo Mode Types
// ============================================================================

export type DemoMode =
  | 'template'      // Process template editing
  | 'workorder'     // Work order progress with part counts
  | 'part-journey'  // Single part's execution history
  | 'evaluation'    // Bottleneck/metrics analysis
  | 'qa-checkpoints'; // QA inspection points

export const DEMO_MODES: { value: DemoMode; label: string; description: string }[] = [
  {
    value: 'template',
    label: 'Process Template',
    description: 'Edit process steps, connections, and properties',
  },
  {
    value: 'workorder',
    label: 'Work Order Progress',
    description: 'View parts at each step in a work order',
  },
  {
    value: 'part-journey',
    label: 'Part Journey',
    description: 'Track a single part through the process',
  },
  {
    value: 'evaluation',
    label: 'Process Evaluation',
    description: 'Analyze bottlenecks and performance metrics',
  },
  {
    value: 'qa-checkpoints',
    label: 'QA Checkpoints',
    description: 'View inspection and sampling requirements',
  },
];
