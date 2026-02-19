import { useState, useCallback, useMemo } from 'react';
import { ReactFlowProvider, type Node, type Edge } from '@xyflow/react';
import { validateProcessFlow, type ValidationResult } from '@/lib/process-validation';
import { ValidationPanel } from '@/components/flow/validation-panel';
import '@xyflow/react/dist/style.css';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FlowCanvas, StepEditorPanel, type StepData } from '@/components/flow';
import { useRetrieveProcesses } from '@/hooks/useRetrieveProcesses';
import { useRetrieveProcessWithSteps } from '@/hooks/useRetrieveProcessWithSteps';
import { useUpdateProcess } from '@/hooks/useUpdateProcessWithSteps';
import { useRetrievePartTypes } from '@/hooks/useRetrievePartTypes';
import { useApproveProcess } from '@/hooks/useApproveProcess';
import { useDeprecateProcess } from '@/hooks/useDeprecateProcess';
import { useDuplicateProcess } from '@/hooks/useDuplicateProcess';
import { useNavigate, useSearch } from '@tanstack/react-router';
import { toast } from 'sonner';
import {
  DEMO_REMANUFACTURING_PROCESS,
  DEMO_STEP_EDGES,
  DEMO_WORKORDER_PART_COUNTS,
  DEMO_WORKORDER_INFO,
  DEMO_PART_JOURNEY,
  DEMO_PART_INFO,
  DEMO_STEP_METRICS,
  calculateBottleneckSeverity,
  DEMO_MODES,
  type DemoMode,
} from '@/lib/demo-data/process-flow-demo';
import {
  Save,
  RotateCcw,
  Plus,
  FileText,
  Package,
  Route,
  BarChart3,
  ClipboardCheck,
  X,
  Circle,
  Play,
  GitBranch,
  RefreshCw,
  Clock,
  CheckCircle,
  MoreVertical,
  Copy,
  Archive,
  ShieldCheck,
  Settings,
  ChevronsUpDown,
  Check,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';

// Map demo modes to icons
const MODE_ICONS: Record<DemoMode, typeof FileText> = {
  template: FileText,
  workorder: Package,
  'part-journey': Route,
  evaluation: BarChart3,
  'qa-checkpoints': ClipboardCheck,
};

// Node type options for adding new steps
const NODE_TYPE_OPTIONS = [
  { type: 'task', label: 'Task Step', icon: Circle, description: 'Standard work step' },
  { type: 'start', label: 'Start Step', icon: Play, description: 'Process entry point' },
  { type: 'decision', label: 'Decision Point', icon: GitBranch, description: 'Branching based on condition' },
  { type: 'rework', label: 'Rework Step', icon: RefreshCw, description: 'Step with visit limit' },
  { type: 'timer', label: 'Timer/Wait Step', icon: Clock, description: 'Step with expected duration' },
  { type: 'terminal', label: 'Terminal Step', icon: CheckCircle, description: 'Process end point' },
] as const;

/**
 * Format milliseconds to human-readable duration.
 */
function formatDuration(ms: number): string {
  if (ms < 60000) return `${Math.round(ms / 1000)}s`;
  if (ms < 3600000) return `${Math.round(ms / 60000)}m`;
  return `${(ms / 3600000).toFixed(1)}h`;
}

export default function ProcessFlowPage() {
  // Read process ID from URL query param (e.g., /process-flow?id=5)
  const searchParams = useSearch({ strict: false }) as { id?: string };
  const initialProcessId = searchParams.id || 'demo';

  const [selectedProcessId, setSelectedProcessId] = useState<string>(initialProcessId);
  const [processSelectOpen, setProcessSelectOpen] = useState(false);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [demoMode, setDemoMode] = useState<DemoMode>('template');
  const [localSteps, setLocalSteps] = useState<StepData[] | null>(null);
  const [localEdges, setLocalEdges] = useState<Edge[] | null>(null);
  const [nextStepId, setNextStepId] = useState(-1); // Negative IDs for new steps (backend ignores negative IDs)

  // Process-level properties (for editing)
  const [localProcessProps, setLocalProcessProps] = useState<{
    name: string;
    part_type: string | null;
    is_remanufactured: boolean;
    is_batch_process: boolean;
  } | null>(null);

  const isDemo = selectedProcessId === 'demo';
  const processId = isDemo ? null : selectedProcessId;

  // Fetch all processes for the selector
  const { data: processesData, isLoading: processesLoading } = useRetrieveProcesses({});

  // Fetch selected process with steps
  const { data: processWithSteps, isLoading: stepsLoading } = useRetrieveProcessWithSteps(
    { params: { id: processId! } },
    { enabled: !!processId }
  );

  // Fetch part types for the selector
  const { data: partTypesData } = useRetrievePartTypes();
  const partTypes = partTypesData?.results || [];

  // Mutations for process actions
  const updateProcess = useUpdateProcess();
  const approveProcess = useApproveProcess();
  const deprecateProcess = useDeprecateProcess();
  const duplicateProcess = useDuplicateProcess();
  const navigate = useNavigate();

  // Initialize local steps when entering edit mode or changing process
  const baseStepsFromSource = useMemo(() => {
    if (isDemo) {
      return DEMO_REMANUFACTURING_PROCESS;
    }
    // Map from new process_steps structure (ProcessStep with nested step)
    const processSteps = processWithSteps?.process_steps || [];
    // Sort by order
    const sortedProcessSteps = [...processSteps].sort((a, b) => (a.order || 0) - (b.order || 0));
    return sortedProcessSteps.map((ps) => {
      const step = ps.step;
      return {
        id: step.id as string,
        name: step.name as string,
        order: ps.order as number, // order is on ProcessStep, not Step
        step_type: step.step_type as StepData['step_type'],
        is_decision_point: step.is_decision_point as boolean | undefined,
        decision_type: step.decision_type as StepData['decision_type'],
        is_terminal: step.is_terminal as boolean | undefined,
        terminal_status: step.terminal_status as StepData['terminal_status'],
        is_entry_point: ps.is_entry_point as boolean | undefined,
        description: step.description as string | undefined,
        max_visits: step.max_visits as number | null,
        expected_duration: step.expected_duration as string | null,
        requires_qa_signoff: step.requires_qa_signoff as boolean | undefined,
        sampling_required: step.sampling_required as boolean | undefined,
        min_sampling_rate: step.min_sampling_rate as number | undefined,
      };
    });
  }, [isDemo, processWithSteps?.process_steps]);

  // Build steps with mode-specific overlay data
  const steps: StepData[] = useMemo(() => {
    // Use local steps if editing, otherwise use base steps from source
    const baseSteps = editMode && localSteps ? localSteps : baseStepsFromSource;

    // For non-demo mode, just return base steps (no overlays needed)
    if (!isDemo) {
      return baseSteps;
    }

    // Enrich demo steps with mode-specific overlay data
    return baseSteps.map((step) => {
      const overlayData: Record<string, unknown> = {};

      switch (demoMode) {
        case 'workorder':
          overlayData.partCount = DEMO_WORKORDER_PART_COUNTS[step.id] || 0;
          overlayData.highlighted = (overlayData.partCount as number) > 0;
          break;

        case 'part-journey': {
          const journeySteps = DEMO_PART_JOURNEY.filter((j) => j.stepId === step.id);
          overlayData.visitedInJourney = journeySteps.length > 0;
          overlayData.journeyVisits = journeySteps;
          overlayData.highlighted = journeySteps.length > 0;
          break;
        }

        case 'evaluation': {
          const metrics = DEMO_STEP_METRICS[step.id];
          const severity = calculateBottleneckSeverity(step.id);
          overlayData.metrics = metrics;
          overlayData.bottleneckSeverity = severity;
          overlayData.isBottleneck = severity >= 0.6;
          overlayData.highlighted = severity >= 0.6;
          break;
        }

        case 'qa-checkpoints':
          overlayData.highlighted = step.requires_qa_signoff || step.sampling_required;
          break;
      }

      return {
        ...step,
        _overlayData: overlayData,
      } as StepData;
    });
  }, [isDemo, baseStepsFromSource, localSteps, editMode, demoMode]);

  // Initialize local steps and process props when entering edit mode
  const initializeLocalSteps = useCallback(() => {
    if (!localSteps) {
      setLocalSteps([...baseStepsFromSource]);
      // Set nextStepId to be higher than any existing step
      const maxId = Math.max(...baseStepsFromSource.map(s => s.id), 0);
      setNextStepId(maxId + 1);
    }
    // Initialize process props if not already set
    if (!localProcessProps && processWithSteps) {
      setLocalProcessProps({
        name: processWithSteps.name || '',
        part_type: processWithSteps.part_type as number | null,
        is_remanufactured: processWithSteps.is_remanufactured || false,
        is_batch_process: processWithSteps.is_batch_process || false,
      });
    }
  }, [baseStepsFromSource, localSteps, localProcessProps, processWithSteps]);

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleAddStep = useCallback((stepType: string) => {
    initializeLocalSteps();

    const currentSteps = localSteps || baseStepsFromSource;
    const maxOrder = Math.max(...currentSteps.map(s => s.order), 0);

    const newStep: StepData = {
      id: nextStepId,
      name: `New ${stepType.charAt(0).toUpperCase() + stepType.slice(1)} Step`,
      order: maxOrder + 1,
      step_type: stepType as StepData['step_type'],
      description: '',
      // Set type-specific defaults
      ...(stepType === 'decision' && {
        is_decision_point: true,
        decision_type: 'manual' as const,
      }),
      ...(stepType === 'terminal' && {
        is_terminal: true,
        terminal_status: 'completed' as const,
      }),
      ...(stepType === 'rework' && {
        max_visits: 3,
      }),
      ...(stepType === 'timer' && {
        expected_duration: '1h',
      }),
    };

    setLocalSteps([...currentSteps, newStep]);
    setNextStepId(nextStepId - 1); // Decrement to get more negative IDs
    setHasChanges(true);

    // Auto-select the new node after a short delay to let React Flow render it
    setTimeout(() => {
      setSelectedNode({
        id: String(nextStepId),
        type: stepType,
        position: { x: 0, y: 0 },
        data: {
          label: newStep.name,
          step: newStep,
          isDecisionPoint: newStep.is_decision_point,
          decisionType: newStep.decision_type,
          isTerminal: newStep.is_terminal,
          terminalStatus: newStep.terminal_status,
          description: newStep.description,
          maxVisits: newStep.max_visits,
          expectedDuration: newStep.expected_duration,
        },
      });
    }, 100);
  }, [localSteps, baseStepsFromSource, nextStepId, initializeLocalSteps]);

  const handleNodeUpdate = useCallback((nodeId: string, data: Partial<StepData>) => {
    initializeLocalSteps();

    setLocalSteps(prev => {
      const steps = prev || baseStepsFromSource;
      return steps.map(step =>
        String(step.id) === nodeId
          ? { ...step, ...data }
          : step
      );
    });

    // Also update selectedNode so the editor panel shows current values
    setSelectedNode(prev => {
      if (!prev || prev.id !== nodeId) return prev;
      const updatedStep = { ...(prev.data as any).step, ...data };
      return {
        ...prev,
        data: {
          ...prev.data,
          label: data.name ?? (prev.data as any).label,
          step: updatedStep,
          isDecisionPoint: updatedStep.is_decision_point,
          decisionType: updatedStep.decision_type,
          isTerminal: updatedStep.is_terminal,
          terminalStatus: updatedStep.terminal_status,
          description: updatedStep.description,
          maxVisits: updatedStep.max_visits,
          expectedDuration: updatedStep.expected_duration,
          requiresQaSignoff: updatedStep.requires_qa_signoff,
          samplingRequired: updatedStep.sampling_required,
          minSamplingRate: updatedStep.min_sampling_rate,
        },
      };
    });

    setHasChanges(true);
  }, [baseStepsFromSource, initializeLocalSteps]);

  const handleNodeDelete = useCallback((nodeId: string) => {
    initializeLocalSteps();

    setLocalSteps(prev => {
      const steps = prev || baseStepsFromSource;
      return steps.filter(step => String(step.id) !== nodeId);
    });
    setSelectedNode(null);
    setHasChanges(true);
  }, [baseStepsFromSource, initializeLocalSteps]);

  const handleSave = useCallback(async () => {
    if (!processId || !localSteps) {
      if (isDemo) {
        toast.info('Demo mode - changes are not persisted');
        setHasChanges(false);
      }
      return;
    }

    try {
      // Build nodes array from local steps (new graph-based format)
      const nodesPayload = localSteps.map((step, index) => ({
        id: step.id > 0 ? step.id : undefined, // Only include ID for existing steps
        _temp_id: step.id <= 0 ? step.id : undefined, // Temp ID for new steps
        name: step.name,
        order: index + 1,
        is_entry_point: index === 0 || step.is_entry_point || false,
        description: step.description || '',
        step_type: step.step_type || 'task',
        is_decision_point: step.is_decision_point || false,
        decision_type: step.decision_type || '',
        is_terminal: step.is_terminal || false,
        terminal_status: step.terminal_status || '',
        max_visits: step.max_visits,
        expected_duration: step.expected_duration,
        requires_qa_signoff: step.requires_qa_signoff || false,
        sampling_required: step.sampling_required || false,
        min_sampling_rate: step.min_sampling_rate,
      }));

      // Build edges array from local edges (new graph-based format)
      const edgesToProcess = localEdges || [];
      const edgesPayload = edgesToProcess.map(edge => {
        const isEscalation = edge.id.endsWith('-esc');
        const isAlternate = edge.id.endsWith('-alt') || edge.sourceHandle === 'fail';
        return {
          from_step: edge.source,
          to_step: edge.target,
          edge_type: isEscalation ? 'escalation' : isAlternate ? 'alternate' : 'default',
        };
      });

      await updateProcess.mutateAsync({
        id: processId,
        data: {
          // Process-level properties
          ...(localProcessProps && {
            name: localProcessProps.name,
            part_type: localProcessProps.part_type,
            is_remanufactured: localProcessProps.is_remanufactured,
            is_batch_process: localProcessProps.is_batch_process,
          }),
          nodes: nodesPayload,
          edges: edgesPayload,
          num_steps: localSteps.length,
        },
      });

      toast.success('Process saved successfully');
      setHasChanges(false);
      setLocalSteps(null); // Reset to refetch fresh data
      setLocalEdges(null);
      setLocalProcessProps(null);
    } catch (error) {
      console.error('Failed to save process:', error);
      toast.error('Failed to save process');
    }
  }, [processId, localSteps, localEdges, localProcessProps, isDemo, updateProcess]);

  // Handler to update process-level properties
  const handleProcessPropChange = useCallback((prop: keyof typeof localProcessProps, value: unknown) => {
    initializeLocalSteps(); // Ensure we have local state initialized
    setLocalProcessProps(prev => {
      if (!prev) {
        // Initialize from current process data
        const initial = {
          name: processWithSteps?.name || '',
          part_type: processWithSteps?.part_type as number | null,
          is_remanufactured: processWithSteps?.is_remanufactured || false,
          is_batch_process: processWithSteps?.is_batch_process || false,
        };
        return { ...initial, [prop]: value };
      }
      return { ...prev, [prop]: value };
    });
    setHasChanges(true);
  }, [initializeLocalSteps, processWithSteps]);

  const handleReset = useCallback(() => {
    setLocalSteps(null);
    setLocalEdges(null);
    setLocalProcessProps(null);
    setHasChanges(false);
    setSelectedNode(null);
  }, []);

  // Track edge changes from the flow canvas
  const handleEdgesChange = useCallback((edges: Edge[]) => {
    // Always capture current edges so we have them for saving
    // But only mark as changed if we're in edit mode with local steps
    const hadPreviousEdges = localEdges !== null;
    setLocalEdges(edges);

    if (editMode && localSteps && hadPreviousEdges) {
      // Only mark changes after initial edge capture
      setHasChanges(true);
    }
  }, [editMode, localSteps, localEdges]);

  const handleApprove = useCallback(async () => {
    if (!processId) return;
    try {
      await approveProcess.mutateAsync(processId);
      toast.success('Process approved successfully');
      setEditMode(false);
    } catch (error) {
      console.error('Failed to approve process:', error);
      toast.error('Failed to approve process');
    }
  }, [processId, approveProcess]);

  const handleDeprecate = useCallback(async () => {
    if (!processId) return;
    try {
      await deprecateProcess.mutateAsync(processId);
      toast.success('Process deprecated');
    } catch (error) {
      console.error('Failed to deprecate process:', error);
      toast.error('Failed to deprecate process');
    }
  }, [processId, deprecateProcess]);

  const handleDuplicate = useCallback(async () => {
    if (!processId) return;
    try {
      const newProcess = await duplicateProcess.mutateAsync({ id: processId });
      toast.success('Process duplicated - opening copy');
      // Navigate to the new process
      setSelectedProcessId(String(newProcess.id));
    } catch (error) {
      console.error('Failed to duplicate process:', error);
      toast.error('Failed to duplicate process');
    }
  }, [processId, duplicateProcess]);

  const processes = processesData?.results || processesData || [];

  // Get current mode info
  const currentModeInfo = DEMO_MODES.find((m) => m.value === demoMode);

  // Get process status and check if editable
  const processStatus = processWithSteps?.status as string | undefined;
  const isProcessEditable = isDemo || processStatus === 'draft';

  // Allow editing in template mode (both demo and real DRAFT processes)
  const canEdit = (demoMode === 'template' || !isDemo) && isProcessEditable;

  // Compute validation for the current process flow
  const validation = useMemo((): ValidationResult => {
    // Get current steps (local if editing, otherwise from source)
    const currentSteps = editMode && localSteps ? localSteps : baseStepsFromSource;

    // Get current edges
    const currentEdges = localEdges || [];

    // Convert steps to Node format for validation
    const nodes: Node[] = currentSteps.map(step => ({
      id: String(step.id),
      type: step.step_type || 'task',
      position: { x: 0, y: 0 },
      data: {
        label: step.name,
        name: step.name,
        step_type: step.step_type,
        is_decision_point: step.is_decision_point,
        is_terminal: step.is_terminal,
        max_visits: step.max_visits,
      },
    }));

    return validateProcessFlow(nodes, currentEdges);
  }, [editMode, localSteps, baseStepsFromSource, localEdges]);

  const hasValidationErrors = !validation.isValid;

  // Build info panel content based on mode
  const infoPanelContent = useMemo(() => {
    if (!isDemo) return null;

    switch (demoMode) {
      case 'workorder':
        return (
          <div className="space-y-2 text-sm">
            <div className="font-medium">{DEMO_WORKORDER_INFO.name}</div>
            <div className="text-muted-foreground">{DEMO_WORKORDER_INFO.description}</div>
            <div className="flex gap-4 text-xs">
              <span>Total Parts: {DEMO_WORKORDER_INFO.totalParts}</span>
              <span>In Progress: {Object.values(DEMO_WORKORDER_PART_COUNTS).reduce((a, b) => a + b, 0) - DEMO_WORKORDER_PART_COUNTS[10] - DEMO_WORKORDER_PART_COUNTS[9]}</span>
            </div>
          </div>
        );

      case 'part-journey':
        return (
          <div className="space-y-2 text-sm">
            <div className="font-medium">Part: {DEMO_PART_INFO.serialNumber}</div>
            <div className="text-muted-foreground">{DEMO_PART_INFO.partType}</div>
            <div className="flex gap-4 text-xs">
              <span>Work Order: {DEMO_PART_INFO.workOrder}</span>
              <Badge variant="secondary">{DEMO_PART_INFO.currentStatus}</Badge>
            </div>
          </div>
        );

      case 'evaluation': {
        const totalParts = Object.values(DEMO_STEP_METRICS).reduce((sum, m) => Math.max(sum, m.totalParts), 0);
        const avgThroughput = Object.values(DEMO_STEP_METRICS).reduce((sum, m) => sum + m.throughput, 0) / Object.keys(DEMO_STEP_METRICS).length;
        return (
          <div className="space-y-2 text-sm">
            <div className="font-medium">Process Performance Analysis</div>
            <div className="flex gap-4 text-xs">
              <span>Total Parts Processed: {totalParts}</span>
              <span>Avg Throughput: {avgThroughput.toFixed(1)}/hr</span>
            </div>
            <div className="text-xs text-orange-600">
              Bottlenecks: Rework (3h), Scrap Decision (4h)
            </div>
          </div>
        );
      }

      case 'qa-checkpoints':
        return (
          <div className="space-y-2 text-sm">
            <div className="font-medium">QA Inspection Points</div>
            <div className="text-muted-foreground">
              2 steps require QA signoff, highlighted below
            </div>
          </div>
        );

      default:
        return null;
    }
  }, [demoMode, isDemo]);

  // Build detail panel for selected node based on mode
  const detailPanelContent = useMemo(() => {
    if (!selectedNode || !isDemo) return null;
    const step = (selectedNode.data as { step?: StepData }).step;
    if (!step) return null;

    const overlayData = (step as StepData & { _overlayData?: Record<string, unknown> })._overlayData || {};

    switch (demoMode) {
      case 'workorder': {
        const partCount = overlayData.partCount as number || 0;
        return (
          <div className="space-y-3">
            <div>
              <Label className="text-xs text-muted-foreground">Parts at Step</Label>
              <div className="text-2xl font-bold">{partCount}</div>
            </div>
            {partCount > 0 && (
              <Button variant="outline" size="sm" className="w-full">
                View Parts List
              </Button>
            )}
          </div>
        );
      }

      case 'part-journey': {
        const journeyVisits = overlayData.journeyVisits as typeof DEMO_PART_JOURNEY || [];
        if (journeyVisits.length === 0) return <div className="text-sm text-muted-foreground">Part did not visit this step</div>;

        return (
          <div className="space-y-3">
            <div>
              <Label className="text-xs text-muted-foreground">Visits</Label>
              <div className="text-lg font-bold">{journeyVisits.length}</div>
            </div>
            {journeyVisits.map((visit, i) => (
              <div key={i} className="text-xs border rounded p-2 space-y-1">
                <div className="flex justify-between">
                  <span>Visit #{visit.visitNumber}</span>
                  {visit.result && (
                    <Badge variant={visit.result === 'pass' ? 'default' : 'destructive'} className="text-xs">
                      {visit.result}
                    </Badge>
                  )}
                </div>
                <div className="text-muted-foreground">
                  {visit.entryTime.toLocaleTimeString()} - {visit.exitTime?.toLocaleTimeString() || 'In Progress'}
                </div>
                {visit.operator && <div>Operator: {visit.operator}</div>}
              </div>
            ))}
          </div>
        );
      }

      case 'evaluation': {
        const metrics = overlayData.metrics as typeof DEMO_STEP_METRICS[number];
        const severity = overlayData.bottleneckSeverity as number || 0;
        if (!metrics) return null;

        return (
          <div className="space-y-3">
            {severity >= 0.6 && (
              <Badge variant="destructive" className="mb-2">
                {severity >= 0.8 ? 'Severe Bottleneck' : 'Bottleneck'}
              </Badge>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-muted-foreground">Avg Dwell Time</Label>
                <div className="text-lg font-bold">{formatDuration(metrics.avgDwellTime)}</div>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Throughput</Label>
                <div className="text-lg font-bold">{metrics.throughput.toFixed(1)}/hr</div>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Total Parts</Label>
                <div className="text-lg font-bold">{metrics.totalParts}</div>
              </div>
              {metrics.passRate !== undefined && (
                <div>
                  <Label className="text-xs text-muted-foreground">Pass Rate</Label>
                  <div className="text-lg font-bold text-green-600">{metrics.passRate}%</div>
                </div>
              )}
            </div>
          </div>
        );
      }

      case 'qa-checkpoints':
        return (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${step.requires_qa_signoff ? 'bg-purple-500' : 'bg-muted'}`} />
              <span className="text-sm">QA Signoff Required: {step.requires_qa_signoff ? 'Yes' : 'No'}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${step.sampling_required ? 'bg-blue-500' : 'bg-muted'}`} />
              <span className="text-sm">Sampling Required: {step.sampling_required ? 'Yes' : 'No'}</span>
            </div>
            {step.min_sampling_rate !== undefined && step.min_sampling_rate > 0 && (
              <div className="text-sm text-muted-foreground">
                Sampling Rate: {step.min_sampling_rate}%
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  }, [selectedNode, demoMode, isDemo]);

  return (
    <div className="h-screen flex flex-col p-3">
      <Card className="flex-1 flex flex-col">
        <CardHeader className="pb-2 pt-4 px-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <CardTitle>
                  Process Flow {demoMode === 'template' && editMode ? 'Editor' : 'Viewer'}
                </CardTitle>
                {!isDemo && processStatus && (
                  <Badge
                    variant={
                      processStatus === 'approved' ? 'default' :
                      processStatus === 'deprecated' ? 'secondary' :
                      'outline'
                    }
                    className={processStatus === 'draft' ? 'border-amber-500 text-amber-600' : ''}
                  >
                    {processStatus.charAt(0).toUpperCase() + processStatus.slice(1)}
                  </Badge>
                )}
              </div>
              <CardDescription>
                {!isDemo && !isProcessEditable
                  ? 'This process is locked. Duplicate to make changes.'
                  : currentModeInfo?.description || 'Visualize manufacturing process steps'}
              </CardDescription>
            </div>
            <div className="flex items-center gap-3">
              {canEdit && (
                <div className="flex items-center gap-2">
                  <Switch
                    id="edit-mode"
                    checked={editMode}
                    onCheckedChange={setEditMode}
                  />
                  <Label htmlFor="edit-mode" className="text-sm">Edit Mode</Label>
                </div>
              )}

              {editMode && (
                <>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="outline" size="sm">
                        <Plus className="h-4 w-4 mr-2" />
                        Add Step
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                      <DropdownMenuLabel>Step Type</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      {NODE_TYPE_OPTIONS.map((option) => {
                        const Icon = option.icon;
                        return (
                          <DropdownMenuItem
                            key={option.type}
                            onClick={() => handleAddStep(option.type)}
                          >
                            <Icon className="h-4 w-4 mr-2" />
                            <div className="flex flex-col">
                              <span>{option.label}</span>
                              <span className="text-xs text-muted-foreground">
                                {option.description}
                              </span>
                            </div>
                          </DropdownMenuItem>
                        );
                      })}
                    </DropdownMenuContent>
                  </DropdownMenu>

                  {hasChanges && (
                    <>
                      <Button variant="outline" size="sm" onClick={handleReset} disabled={updateProcess.isPending}>
                        <RotateCcw className="h-4 w-4 mr-2" />
                        Reset
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleSave}
                        disabled={updateProcess.isPending || hasValidationErrors}
                        title={hasValidationErrors ? 'Fix validation errors before saving' : undefined}
                      >
                        {updateProcess.isPending ? (
                          <>
                            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Save className="h-4 w-4 mr-2" />
                            Save
                          </>
                        )}
                      </Button>
                    </>
                  )}
                </>
              )}

              <Popover open={processSelectOpen} onOpenChange={setProcessSelectOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={processSelectOpen}
                    className="w-[350px] justify-between font-normal"
                  >
                    <span className="truncate">
                      {selectedProcessId === 'demo'
                        ? 'Demo: Remanufacturing Process'
                        : (processes as { id: number; name: string }[]).find(
                            (p) => p.id.toString() === selectedProcessId
                          )?.name || 'Select a process...'}
                    </span>
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[350px] p-0">
                  <Command>
                    <CommandInput placeholder="Search processes..." />
                    <CommandList>
                      <CommandEmpty>No process found.</CommandEmpty>
                      <CommandGroup heading="Demo">
                        <CommandItem
                          value="demo remanufacturing"
                          onSelect={() => {
                            setSelectedProcessId('demo');
                            setSelectedNode(null);
                            setEditMode(false);
                            setHasChanges(false);
                            setLocalSteps(null);
                            setProcessSelectOpen(false);
                          }}
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              selectedProcessId === 'demo' ? "opacity-100" : "opacity-0"
                            )}
                          />
                          <Badge variant="secondary" className="mr-2 text-xs">Demo</Badge>
                          Remanufacturing Process
                        </CommandItem>
                      </CommandGroup>
                      <CommandGroup heading="Processes">
                        {processesLoading ? (
                          <div className="p-2">
                            <Skeleton className="h-4 w-full" />
                          </div>
                        ) : (
                          (processes as { id: string; name: string; status?: string }[]).map((p) => (
                            <CommandItem
                              key={p.id}
                              value={p.name}
                              onSelect={() => {
                                setSelectedProcessId(p.id.toString());
                                setSelectedNode(null);
                                setEditMode(false);
                                setHasChanges(false);
                                setLocalSteps(null);
                                setProcessSelectOpen(false);
                              }}
                            >
                              <Check
                                className={cn(
                                  "mr-2 h-4 w-4",
                                  selectedProcessId === p.id.toString() ? "opacity-100" : "opacity-0"
                                )}
                              />
                              {p.name}
                            </CommandItem>
                          ))
                        )}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>

              {/* Process Actions */}
              {!isDemo && processId && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="icon" className="h-9 w-9">
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Process Actions</DropdownMenuLabel>
                    <DropdownMenuSeparator />

                    {/* Approve - only for draft */}
                    {processStatus === 'draft' && (
                      <DropdownMenuItem
                        onClick={handleApprove}
                        disabled={approveProcess.isPending || hasChanges || hasValidationErrors}
                      >
                        <ShieldCheck className="h-4 w-4 mr-2 text-green-600" />
                        <div className="flex flex-col">
                          <span>Approve</span>
                          <span className="text-xs text-muted-foreground">
                            {hasValidationErrors
                              ? 'Fix validation errors first'
                              : hasChanges
                                ? 'Save changes first'
                                : 'Lock for production use'}
                          </span>
                        </div>
                      </DropdownMenuItem>
                    )}

                    {/* Deprecate - only for approved */}
                    {processStatus === 'approved' && (
                      <DropdownMenuItem
                        onClick={handleDeprecate}
                        disabled={deprecateProcess.isPending}
                      >
                        <Archive className="h-4 w-4 mr-2 text-orange-600" />
                        <div className="flex flex-col">
                          <span>Deprecate</span>
                          <span className="text-xs text-muted-foreground">
                            Hide from new work orders
                          </span>
                        </div>
                      </DropdownMenuItem>
                    )}

                    {/* Duplicate - always available */}
                    <DropdownMenuItem
                      onClick={handleDuplicate}
                      disabled={duplicateProcess.isPending}
                    >
                      <Copy className="h-4 w-4 mr-2 text-blue-600" />
                      <div className="flex flex-col">
                        <span>Duplicate</span>
                        <span className="text-xs text-muted-foreground">
                          Create editable copy
                        </span>
                      </div>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>

          {/* Demo Mode Tabs */}
          {isDemo && (
            <div className="mt-2">
              <Tabs value={demoMode} onValueChange={(v) => setDemoMode(v as DemoMode)}>
                <TabsList className="grid w-full grid-cols-5 h-9">
                  {DEMO_MODES.map((mode) => {
                    const Icon = MODE_ICONS[mode.value];
                    return (
                      <TabsTrigger key={mode.value} value={mode.value} className="flex items-center gap-2">
                        <Icon className="h-4 w-4" />
                        <span className="hidden sm:inline">{mode.label}</span>
                      </TabsTrigger>
                    );
                  })}
                </TabsList>
              </Tabs>
            </div>
          )}

          {/* Mode Info Panel */}
          {infoPanelContent && (
            <div className="mt-2 p-2 bg-muted/50 rounded-md text-sm">
              {infoPanelContent}
            </div>
          )}
        </CardHeader>

        <CardContent className="flex-1 flex gap-3 p-0 px-4 pb-4 min-h-0">
          <div className="flex-1 border rounded-lg overflow-hidden bg-background">
            {!isDemo && stepsLoading ? (
              <div className="flex items-center justify-center h-full">
                <Skeleton className="h-32 w-64" />
              </div>
            ) : steps.length === 0 ? (
              <div className="flex items-center justify-center h-full text-muted-foreground flex-col gap-4">
                <p>No steps defined for this process</p>
                {editMode && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button size="sm">
                        <Plus className="h-4 w-4 mr-2" />
                        Add First Step
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-56">
                      <DropdownMenuLabel>Step Type</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      {NODE_TYPE_OPTIONS.map((option) => {
                        const Icon = option.icon;
                        return (
                          <DropdownMenuItem
                            key={option.type}
                            onClick={() => handleAddStep(option.type)}
                          >
                            <Icon className="h-4 w-4 mr-2" />
                            <div className="flex flex-col">
                              <span>{option.label}</span>
                              <span className="text-xs text-muted-foreground">
                                {option.description}
                              </span>
                            </div>
                          </DropdownMenuItem>
                        );
                      })}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
            ) : (
              <ReactFlowProvider>
                <FlowCanvas
                  steps={steps}
                  stepEdges={isDemo ? DEMO_STEP_EDGES : processWithSteps?.step_edges}
                  selectedNode={selectedNode}
                  onNodeClick={onNodeClick}
                  onPaneClick={onPaneClick}
                  onDeleteNode={handleNodeDelete}
                  onEdgesChange={handleEdgesChange}
                  editable={editMode}
                  demoMode={isDemo ? demoMode : undefined}
                />
              </ReactFlowProvider>
            )}
          </div>

          {/* Right Panel - Step editor or Process settings */}
          {(selectedNode || (editMode && !isDemo)) && (
            <div className="w-80 shrink-0 space-y-3 overflow-y-auto max-h-full">
              {/* Validation Panel - show when editing */}
              {editMode && !isDemo && (
                <ValidationPanel
                  validation={validation}
                  onSelectNode={(nodeId) => {
                    // Find the node and select it
                    const step = (localSteps || baseStepsFromSource).find(s => String(s.id) === nodeId);
                    if (step) {
                      setSelectedNode({
                        id: nodeId,
                        type: step.step_type || 'task',
                        position: { x: 0, y: 0 },
                        data: { ...step, label: step.name },
                      });
                    }
                  }}
                />
              )}

              {selectedNode ? (
                // Step is selected - show step editor
                demoMode === 'template' || !isDemo ? (
                  <StepEditorPanel
                    node={selectedNode}
                    onUpdate={handleNodeUpdate}
                    onDelete={handleNodeDelete}
                    onClose={() => setSelectedNode(null)}
                    editable={editMode}
                  />
                ) : (
                  <Card>
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <CardTitle className="text-lg">
                            {(selectedNode.data as { label?: string }).label}
                          </CardTitle>
                          <CardDescription>
                            {currentModeInfo?.label} Details
                          </CardDescription>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 -mr-2 -mt-1"
                          onClick={() => setSelectedNode(null)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      {detailPanelContent}
                    </CardContent>
                  </Card>
                )
              ) : (
                // No step selected in edit mode - show process settings
                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-2">
                      <Settings className="h-5 w-5" />
                      <div>
                        <CardTitle className="text-lg">Process Settings</CardTitle>
                        <CardDescription>Configure process properties</CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Process Name */}
                    <div className="space-y-1.5">
                      <Label htmlFor="process-name">Name</Label>
                      <Input
                        id="process-name"
                        value={localProcessProps?.name ?? processWithSteps?.name ?? ''}
                        onChange={(e) => handleProcessPropChange('name', e.target.value)}
                        placeholder="Process name"
                      />
                    </div>

                    {/* Part Type */}
                    <div className="space-y-1.5">
                      <Label htmlFor="part-type">Part Type</Label>
                      <Select
                        value={String(localProcessProps?.part_type ?? processWithSteps?.part_type ?? '')}
                        onValueChange={(v) => handleProcessPropChange('part_type', v)}
                      >
                        <SelectTrigger id="part-type">
                          <SelectValue placeholder="Select part type..." />
                        </SelectTrigger>
                        <SelectContent>
                          {(partTypes as { id: string; name: string }[]).map((pt) => (
                            <SelectItem key={pt.id} value={pt.id.toString()}>
                              {pt.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <Separator />

                    {/* Is Remanufactured */}
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label htmlFor="is-reman">Remanufacturing</Label>
                        <p className="text-xs text-muted-foreground">Process handles used/core parts</p>
                      </div>
                      <Switch
                        id="is-reman"
                        checked={localProcessProps?.is_remanufactured ?? processWithSteps?.is_remanufactured ?? false}
                        onCheckedChange={(checked) => handleProcessPropChange('is_remanufactured', checked)}
                      />
                    </div>

                    {/* Is Batch Process */}
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label htmlFor="is-batch">Batch Processing</Label>
                        <p className="text-xs text-muted-foreground">Parts move through steps together</p>
                      </div>
                      <Switch
                        id="is-batch"
                        checked={localProcessProps?.is_batch_process ?? processWithSteps?.is_batch_process ?? false}
                        onCheckedChange={(checked) => handleProcessPropChange('is_batch_process', checked)}
                      />
                    </div>

                    <Separator />

                    {/* Read-only info */}
                    <div className="text-xs text-muted-foreground space-y-1">
                      <p><span className="font-medium">Steps:</span> {steps.length}</p>
                      <p><span className="font-medium">Status:</span> {processStatus ?? 'Unknown'}</p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
