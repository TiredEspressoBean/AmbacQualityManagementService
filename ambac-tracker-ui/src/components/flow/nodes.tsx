import { memo } from 'react';
import { Position } from '@xyflow/react';
import { BaseNode, BaseNodeHeader, BaseNodeHeaderTitle, BaseNodeContent } from './base-node';
import { BaseHandle } from './base-handle';
import { LabeledHandle } from './labeled-handle';
import { cn } from '@/lib/utils';
import {
  CheckCircle,
  GitBranch,
  Circle,
  Play,
  Truck,
  Package,
  Trash2,
  Undo2,
  Clock,
  PackageOpen,
  RefreshCw,
  ClipboardCheck,
  FlaskConical,
  AlertTriangle,
} from 'lucide-react';
import type { DemoMode } from '@/lib/demo-data/process-flow-demo';
import type { NodeMetrics } from './types';

export interface StepNodeData {
  label: string;
  step?: unknown & {
    _overlayData?: {
      partCount?: number;
      highlighted?: boolean;
      visitedInJourney?: boolean;
      journeyVisits?: unknown[];
      metrics?: NodeMetrics;
      bottleneckSeverity?: number;
      isBottleneck?: boolean;
    };
    requires_qa_signoff?: boolean;
    sampling_required?: boolean;
    min_sampling_rate?: number;
  };
  isDecisionPoint?: boolean;
  decisionType?: string;
  isTerminal?: boolean;
  terminalStatus?: string;
  description?: string;
  /** For highlighting current step in work order tracking */
  highlighted?: boolean;
  /** Part count badge */
  partCount?: number;
  /** Current visit number for rework nodes */
  visitNumber?: number;
  /** Max visits allowed for rework nodes */
  maxVisits?: number;
  /** Expected duration for timer display */
  expectedDuration?: string;
  /** Whether this is the start node (no incoming edges) */
  isStart?: boolean;
  /** Demo mode for conditional overlay rendering */
  demoMode?: DemoMode;
}

// Props for our custom step nodes
interface StepNodeProps {
  data: StepNodeData;
  selected?: boolean;
}

/** Format milliseconds to human-readable duration */
function formatDuration(ms: number): string {
  if (ms < 60000) return `${Math.round(ms / 1000)}s`;
  if (ms < 3600000) return `${Math.round(ms / 60000)}m`;
  return `${(ms / 3600000).toFixed(1)}h`;
}

/** Render overlay badges based on demo mode */
function NodeOverlays({ data }: { data: StepNodeData }) {
  const { demoMode, step } = data;
  const overlayData = (step as StepNodeData['step'])?._overlayData;

  if (!demoMode || !overlayData) return null;

  switch (demoMode) {
    case 'workorder':
      if (overlayData.partCount && overlayData.partCount > 0) {
        return (
          <div className="absolute -top-2 -right-2 flex items-center gap-1 px-1.5 py-0.5 rounded-full text-xs font-medium bg-primary text-primary-foreground shadow-sm z-10">
            <Package className="h-3 w-3" />
            <span>{overlayData.partCount}</span>
          </div>
        );
      }
      return null;

    case 'part-journey':
      if (overlayData.visitedInJourney && overlayData.journeyVisits) {
        const visits = overlayData.journeyVisits.length;
        return (
          <div className="absolute -top-2 -right-2 flex items-center gap-1 px-1.5 py-0.5 rounded-full text-xs font-medium bg-blue-500 text-white shadow-sm z-10">
            <CheckCircle className="h-3 w-3" />
            {visits > 1 && <span>{visits}x</span>}
          </div>
        );
      }
      return null;

    case 'evaluation':
      if (overlayData.metrics) {
        const severity = overlayData.bottleneckSeverity || 0;
        const bgColor = severity >= 0.8
          ? 'bg-red-500'
          : severity >= 0.6
            ? 'bg-orange-500'
            : 'bg-muted';
        const textColor = severity >= 0.6 ? 'text-white' : 'text-muted-foreground';

        return (
          <div className={cn(
            'absolute -top-2 -right-2 flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium shadow-sm z-10',
            bgColor,
            textColor
          )}>
            {severity >= 0.6 && <AlertTriangle className="h-3 w-3" />}
            <Clock className="h-3 w-3" />
            <span>{formatDuration(overlayData.metrics.avgDwellTime)}</span>
          </div>
        );
      }
      return null;

    case 'qa-checkpoints': {
      const stepData = step as StepNodeData['step'];
      const hasQa = stepData?.requires_qa_signoff;
      const hasSampling = stepData?.sampling_required;

      if (hasQa || hasSampling) {
        return (
          <div className="absolute -top-2 -right-2 flex items-center gap-1 z-10">
            {hasQa && (
              <div className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-purple-500 text-white shadow-sm">
                <ClipboardCheck className="h-3 w-3" />
              </div>
            )}
            {hasSampling && (
              <div className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-blue-500 text-white shadow-sm">
                <FlaskConical className="h-3 w-3" />
                <span>{stepData?.min_sampling_rate}%</span>
              </div>
            )}
          </div>
        );
      }
      return null;
    }

    default:
      return null;
  }
}

/** Get highlight styling based on demo mode */
function getHighlightClass(data: StepNodeData): string {
  const overlayData = (data.step as StepNodeData['step'])?._overlayData;

  if (!data.demoMode || !overlayData?.highlighted) return '';

  switch (data.demoMode) {
    case 'workorder':
      return 'ring-2 ring-primary';
    case 'part-journey':
      return 'ring-2 ring-blue-500 bg-blue-50/50 dark:bg-blue-950/30';
    case 'evaluation': {
      const severity = overlayData.bottleneckSeverity || 0;
      if (severity >= 0.8) return 'ring-2 ring-red-500 shadow-red-500/30 shadow-lg';
      if (severity >= 0.6) return 'ring-2 ring-orange-500 shadow-orange-500/20 shadow-lg';
      return '';
    }
    case 'qa-checkpoints':
      return 'ring-2 ring-purple-500';
    default:
      return data.highlighted ? 'ring-2 ring-primary' : '';
  }
}

/** Standard task/step node */
export const TaskNode = memo(({ data }: StepNodeProps) => {
  return (
    <BaseNode className={cn(getHighlightClass(data))}>
      <NodeOverlays data={data} />
      <BaseHandle type="target" position={Position.Left} />
      <BaseNodeHeader>
        <Circle className="h-3 w-3 text-muted-foreground" />
        <BaseNodeHeaderTitle>{data.label}</BaseNodeHeaderTitle>
      </BaseNodeHeader>
      {data.description && (
        <BaseNodeContent>
          <p className="text-xs text-muted-foreground line-clamp-2">
            {data.description}
          </p>
        </BaseNodeContent>
      )}
      <BaseHandle type="source" position={Position.Right} />
    </BaseNode>
  );
});
TaskNode.displayName = 'TaskNode';

/** Decision point node with pass/fail outputs */
export const DecisionNode = memo(({ data }: StepNodeProps) => {
  return (
    <BaseNode className={cn(
      "border-amber-500",
      getHighlightClass(data)
    )}>
      <NodeOverlays data={data} />
      <BaseHandle type="target" position={Position.Left} />
      <BaseNodeHeader className="bg-amber-50 dark:bg-amber-950/30">
        <GitBranch className="h-3 w-3 text-amber-600" />
        <BaseNodeHeaderTitle>{data.label}</BaseNodeHeaderTitle>
      </BaseNodeHeader>
      <BaseNodeContent>
        <p className="text-xs text-muted-foreground">
          {data.decisionType === 'qa_result' && 'QA Pass/Fail'}
          {data.decisionType === 'measurement' && 'Measurement Check'}
          {data.decisionType === 'manual' && 'Manual Decision'}
        </p>
      </BaseNodeContent>
      <div className="flex flex-col gap-1 pr-1">
        <LabeledHandle
          type="source"
          position={Position.Right}
          id="pass"
          title="Pass"
          labelClassName="text-xs text-green-600"
          handleClassName="!bg-green-500 !border-green-600"
        />
        <LabeledHandle
          type="source"
          position={Position.Right}
          id="fail"
          title="Fail"
          labelClassName="text-xs text-red-600"
          handleClassName="!bg-red-500 !border-red-600"
        />
      </div>
    </BaseNode>
  );
});
DecisionNode.displayName = 'DecisionNode';

/** Start node - entry point with no input handle */
export const StartNode = memo(({ data }: StepNodeProps) => {
  return (
    <BaseNode className={cn(
      "border-green-500",
      getHighlightClass(data)
    )}>
      <NodeOverlays data={data} />
      <BaseNodeHeader className="bg-green-50 dark:bg-green-950/30">
        <Play className="h-3 w-3 text-green-600" />
        <BaseNodeHeaderTitle>{data.label}</BaseNodeHeaderTitle>
      </BaseNodeHeader>
      {data.description && (
        <BaseNodeContent>
          <p className="text-xs text-muted-foreground line-clamp-2">
            {data.description}
          </p>
        </BaseNodeContent>
      )}
      <BaseHandle type="source" position={Position.Right} />
    </BaseNode>
  );
});
StartNode.displayName = 'StartNode';

/** Rework node - task with visit counter badge */
export const ReworkNode = memo(({ data }: StepNodeProps) => {
  return (
    <BaseNode className={cn(
      "border-orange-500",
      getHighlightClass(data)
    )}>
      <NodeOverlays data={data} />
      <BaseHandle type="target" position={Position.Left} />
      <BaseNodeHeader className="bg-orange-50 dark:bg-orange-950/30">
        <RefreshCw className="h-3 w-3 text-orange-600" />
        <BaseNodeHeaderTitle>{data.label}</BaseNodeHeaderTitle>
        {data.maxVisits && (
          <span className="text-xs bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-300 px-1.5 py-0.5 rounded-full font-medium">
            {data.visitNumber ?? '?'}/{data.maxVisits}
          </span>
        )}
      </BaseNodeHeader>
      {data.description && (
        <BaseNodeContent>
          <p className="text-xs text-muted-foreground line-clamp-2">
            {data.description}
          </p>
        </BaseNodeContent>
      )}
      <BaseHandle type="source" position={Position.Right} />
    </BaseNode>
  );
});
ReworkNode.displayName = 'ReworkNode';

/** Timer node - task with duration display */
export const TimerNode = memo(({ data }: StepNodeProps) => {
  return (
    <BaseNode className={cn(
      "border-blue-500",
      getHighlightClass(data)
    )}>
      <NodeOverlays data={data} />
      <BaseHandle type="target" position={Position.Left} />
      <BaseNodeHeader className="bg-blue-50 dark:bg-blue-950/30">
        <Clock className="h-3 w-3 text-blue-600" />
        <BaseNodeHeaderTitle>{data.label}</BaseNodeHeaderTitle>
        {data.expectedDuration && (
          <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded-full font-medium">
            {data.expectedDuration}
          </span>
        )}
      </BaseNodeHeader>
      {data.description && (
        <BaseNodeContent>
          <p className="text-xs text-muted-foreground line-clamp-2">
            {data.description}
          </p>
        </BaseNodeContent>
      )}
      <BaseHandle type="source" position={Position.Right} />
    </BaseNode>
  );
});
TimerNode.displayName = 'TimerNode';

/** Terminal config by status */
const terminalConfig: Record<string, { icon: typeof CheckCircle; color: string; bgClass: string; textClass: string }> = {
  completed: { icon: CheckCircle, color: 'green', bgClass: 'bg-green-50 dark:bg-green-950/30', textClass: 'text-green-600' },
  shipped: { icon: Truck, color: 'green', bgClass: 'bg-green-50 dark:bg-green-950/30', textClass: 'text-green-600' },
  stock: { icon: Package, color: 'blue', bgClass: 'bg-blue-50 dark:bg-blue-950/30', textClass: 'text-blue-600' },
  scrapped: { icon: Trash2, color: 'red', bgClass: 'bg-red-50 dark:bg-red-950/30', textClass: 'text-red-600' },
  returned: { icon: Undo2, color: 'orange', bgClass: 'bg-orange-50 dark:bg-orange-950/30', textClass: 'text-orange-600' },
  awaiting_pickup: { icon: Clock, color: 'yellow', bgClass: 'bg-yellow-50 dark:bg-yellow-950/30', textClass: 'text-yellow-600' },
  core_banked: { icon: PackageOpen, color: 'blue', bgClass: 'bg-blue-50 dark:bg-blue-950/30', textClass: 'text-blue-600' },
  rma_closed: { icon: CheckCircle, color: 'gray', bgClass: 'bg-gray-50 dark:bg-gray-800/30', textClass: 'text-gray-600' },
};

/** Terminal/end state node - adapts styling based on terminal_status */
export const TerminalNode = memo(({ data }: StepNodeProps) => {
  const config = terminalConfig[data.terminalStatus || 'completed'] || terminalConfig.completed;
  const Icon = config.icon;
  const borderClass = `border-${config.color}-500`;

  return (
    <BaseNode className={cn(
      borderClass,
      getHighlightClass(data)
    )}>
      <NodeOverlays data={data} />
      <BaseHandle type="target" position={Position.Left} />
      <BaseNodeHeader className={config.bgClass}>
        <Icon className={cn("h-3 w-3", config.textClass)} />
        <BaseNodeHeaderTitle>{data.label}</BaseNodeHeaderTitle>
      </BaseNodeHeader>
      {data.terminalStatus && (
        <BaseNodeContent>
          <span className={cn("text-xs font-medium", config.textClass)}>
            {data.terminalStatus.replace('_', ' ')}
          </span>
        </BaseNodeContent>
      )}
    </BaseNode>
  );
});
TerminalNode.displayName = 'TerminalNode';

/** Node types map for ReactFlow */
export const flowNodeTypes = {
  task: TaskNode,
  start: StartNode,
  decision: DecisionNode,
  rework: ReworkNode,
  timer: TimerNode,
  terminal: TerminalNode,
};
