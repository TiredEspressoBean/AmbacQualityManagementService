import { useState } from 'react';
import type { Node } from '@xyflow/react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { DurationInput } from '@/components/ui/duration-input';
import { Trash2, X, Ruler, Target, Settings, FileText, Eye, ListChecks, ArrowRight, ChevronDown } from 'lucide-react';
import { useNavigate } from '@tanstack/react-router';
import { useSubsteps } from '@/hooks/useSubsteps';
import type { StepData } from './use-steps-to-flow';
import { useRetrieveMeasurementDefinitions } from '@/hooks/useRetrieveMeasurementDefinitions';
import { useRetrieveCompanies } from '@/hooks/useRetrieveCompanies';
import { useRetrieveStepWithSamplingRules } from '@/hooks/useRetrieveStepWithSamplingRules';
import { useRetrieveDocuments } from '@/hooks/useRetrieveDocuments';
import { useContentTypeMapping } from '@/hooks/useContentTypes';
import { MeasurementsEditor } from './measurements-editor';
import { StepSamplingEditor } from './step-sampling-editor';
import { StepDocumentsEditor } from './step-documents-editor';
import { parseDurationToMinutes, formatMinutesToDuration, formatDurationDisplay } from '@/lib/duration-utils';

/** Terminal status options */
export const TERMINAL_STATUS_OPTIONS = [
  { value: 'COMPLETED', label: 'Completed Successfully' },
  { value: 'SHIPPED', label: 'Shipped to Customer' },
  { value: 'STOCK', label: 'Put into Inventory' },
  { value: 'SCRAPPED', label: 'Scrapped' },
  { value: 'RETURNED', label: 'Returned to Supplier' },
  { value: 'AWAITING_PICKUP', label: 'Awaiting Customer Pickup' },
  { value: 'CORE_BANKED', label: 'Core Banked' },
  { value: 'RMA_CLOSED', label: 'RMA Closed' },
] as const;

/** Decision type options */
export const DECISION_TYPE_OPTIONS = [
  { value: 'QA_RESULT', label: 'Based on QA Pass/Fail' },
  { value: 'MEASUREMENT', label: 'Based on Measurement Threshold' },
  { value: 'MANUAL', label: 'Manual Operator Selection' },
  { value: 'AGGREGATE', label: 'Based on Quality Gate (aggregate signal)' },
] as const;

/** First Piece Inspection scope options */
export const FPI_SCOPE_OPTIONS = [
  { value: 'PER_WORKORDER', label: 'Per Work Order' },
  { value: 'PER_SHIFT', label: 'Per Shift' },
  { value: 'PER_EQUIPMENT', label: 'Per Equipment' },
  { value: 'PER_OPERATOR', label: 'Per Operator' },
] as const;

export interface StepEditorPanelProps {
  node: Node;
  onUpdate: (nodeId: string, data: Partial<StepData>) => void;
  onDelete: (nodeId: string) => void;
  onClose?: () => void;
  editable: boolean;
  /** Owning process id — enables navigation into the substep editor.
   *  Omit (or pass null) when the panel is used in demo mode without a
   *  persisted process. */
  processId?: string | null;
  /** Quick-add "route rejected items to …" — candidate destination steps a
   *  reject can route to (excludes this step, the start step, and any step
   *  this one already routes rejects to). Undefined disables the affordance. */
  rejectDestinations?: { id: string; label: string; hint?: string }[];
  /** Steps this one already routes rejects to (rendered as removable-by-canvas
   *  chips so the author can see the wiring without reading the graph). */
  rejectRoutes?: { id: string; label: string }[];
  /** Create a reject (ALTERNATE) edge from this step to the given target. */
  onAddRejectEdge?: (targetId: string) => void;
}

export function StepEditorPanel({ node, onUpdate, onDelete, onClose, editable, processId, rejectDestinations, rejectRoutes, onAddRejectEdge }: StepEditorPanelProps) {
  const navigate = useNavigate();
  const [rejectTarget, setRejectTarget] = useState<string>('');
  const [advancedOpen, setAdvancedOpen] = useState(false);

  // Type-driven relevance: the step's node type decides which sections matter,
  // so we don't dump every possible setting on every step. Settings implied by
  // the type (a Decision node IS a decision point; a Terminal node IS terminal)
  // are shown as their meaningful field (decision type / end status) rather than
  // a redundant on/off toggle. The rest lives under "Advanced".
  const nodeType = String(node.type || (node.data as any)?.step_type || 'TASK');
  const decisionTypeValue = (node.data as any)?.decisionType ?? (node.data as any)?.decision_type;
  const isDecisionType = nodeType === 'DECISION';
  const isTerminalType = nodeType === 'TERMINAL';
  const isReworkType = nodeType === 'REWORK';
  const isTimerType = nodeType === 'TIMER';
  const isStartType = nodeType === 'START';
  const isReceivingType = nodeType === 'RECEIVING';
  // A step behaves as a decision if it's a Decision node or was flagged one.
  const actsAsDecision = isDecisionType || !!(node.data as any)?.isDecisionPoint;
  const actsAsTerminal = isTerminalType || !!(node.data as any)?.isTerminal;
  // Measurements/sampling/docs/substeps only make sense on working steps.
  const showConfiguration = !isStartType && !isTerminalType;
  // Reject routing is the Fail/alternate branch — relevant to any decision/gate step.
  const showRejectRouting = !!onAddRejectEdge && (actsAsDecision || decisionTypeValue === 'AGGREGATE');
  // eslint-disable-next-line local/no-as-any -- FlowNodeData is a union type; we use structural access for the step sub-shape here
  const data = node.data as any;
  const stepId = data.step?.id as string | undefined;

  // State for editor dialogs
  const [measurementsOpen, setMeasurementsOpen] = useState(false);
  const [samplingOpen, setSamplingOpen] = useState(false);
  const [documentsOpen, setDocumentsOpen] = useState(false);

  // Get content type ID for steps
  const { getContentTypeId, isLoading: contentTypesLoading } = useContentTypeMapping();
  const stepsContentTypeId = getContentTypeId('steps');

  // Fetch measurement count
  const { data: measurementsResponse } = useRetrieveMeasurementDefinitions(
    { step: stepId },
    undefined,
    { enabled: !!stepId }
  );
  const measurementCount = measurementsResponse?.count ?? 0;

  // Substep count — enables a "Substeps (N)" affordance that drills into the
  // DWI substep editor for this step.
  const { data: substepsResponse } = useSubsteps(stepId ? { step: stepId } : undefined);
  const substepCount = substepsResponse?.count ?? 0;

  // Fetch sampling rules count
  const { data: stepWithRules } = useRetrieveStepWithSamplingRules(
    { params: { id: stepId! } },
    { enabled: !!stepId }
  );
  // active_ruleset may be on the extended type from the hook
  // eslint-disable-next-line local/no-as-any -- active_ruleset is not in Schema<"ProcessStep">; backend returns it via extended serializer (FLAG: add active_ruleset to ProcessStepSerializer)
  const samplingRuleCount = (stepWithRules as any)?.active_ruleset?.rules?.length ?? 0;

  // Fetch document count
  const { data: documentsResponse } = useRetrieveDocuments(
    {
      content_type: stepsContentTypeId,
      object_id: stepId,
    },
    undefined,
    { enabled: !!stepId && !!stepsContentTypeId && !contentTypesLoading }
  );
  const documentCount = documentsResponse?.count ?? 0;

  // Vendor options for an outside-process (subcontract) receiving node.
  const { data: companiesData } = useRetrieveCompanies(
    { limit: 200 } as never, undefined, { enabled: isReceivingType },
  );
  const companies = (companiesData?.results ?? []) as { id: string; name: string }[];

  return (
    <Card className="w-full shrink-0">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            Step Details
            <Badge variant="outline">{node.type}</Badge>
          </CardTitle>
          {onClose && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 -mr-2 -mt-1"
              onClick={onClose}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Name */}
        <div className="space-y-1.5">
          <Label htmlFor="step-name">Name</Label>
          {editable ? (
            <Input
              id="step-name"
              value={data.label || ''}
              onChange={(e) => onUpdate(node.id, { name: e.target.value })}
            />
          ) : (
            <p className="text-sm font-medium">{data.label}</p>
          )}
        </div>

        {/* Description */}
        <div className="space-y-1.5">
          <Label htmlFor="step-description">Description</Label>
          {editable ? (
            <Textarea
              id="step-description"
              value={data.description || ''}
              onChange={(e) => onUpdate(node.id, { description: e.target.value })}
              rows={3}
            />
          ) : (
            <p className="text-sm text-muted-foreground">
              {data.description || 'No description'}
            </p>
          )}
        </div>

        {/* DECISION / gate steps: decision type + where rejects go. The node
            being a Decision step already implies "decision point" — no toggle. */}
        {actsAsDecision && (
          <>
            <Separator />
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label>Decision type</Label>
                {editable ? (
                  <Select
                    value={data.decisionType || ''}
                    // eslint-disable-next-line local/no-as-any -- decision_type is a string enum; Select returns string and the update fn accepts the wider type
                    onValueChange={(v) => onUpdate(node.id, { decision_type: v as any })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="How is the outcome decided?" />
                    </SelectTrigger>
                    <SelectContent>
                      {DECISION_TYPE_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Badge variant="outline">{data.decisionType || 'Not set'}</Badge>
                )}
              </div>

              {/* Route rejected items to … — form-style reject/alternate edge.
                  Picking a step + Add wires it without touching the canvas. */}
              {showRejectRouting && editable && (
                <div className="space-y-2">
                  <Label className="text-sm font-normal">Route rejected items to…</Label>
                  {rejectRoutes && rejectRoutes.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {rejectRoutes.map((r) => (
                        <Badge key={r.id} variant="secondary" className="gap-1">
                          <ArrowRight className="h-3 w-3" />
                          {r.label}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <Select value={rejectTarget} onValueChange={setRejectTarget}>
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Choose a destination…" />
                      </SelectTrigger>
                      <SelectContent>
                        {(rejectDestinations ?? []).map((d) => (
                          <SelectItem key={d.id} value={d.id}>
                            {d.label}{d.hint ? ` — ${d.hint}` : ''}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      size="sm"
                      disabled={!rejectTarget}
                      onClick={() => {
                        if (!rejectTarget) return;
                        onAddRejectEdge?.(rejectTarget);
                        setRejectTarget('');
                      }}
                    >
                      Add
                    </Button>
                  </div>
                  {(rejectDestinations ?? []).length === 0 && (
                    <p className="text-xs text-muted-foreground">
                      No other steps yet — add a destination (e.g. a Scrap or Quarantine
                      step) to route rejects to.
                    </p>
                  )}
                </div>
              )}
            </div>
          </>
        )}

        {/* TERMINAL steps: just the end status (terminal is implied by the type). */}
        {actsAsTerminal && (
          <>
            <Separator />
            <div className="space-y-1.5">
              <Label>End status</Label>
              {editable ? (
                <Select
                  value={data.terminalStatus || ''}
                  // eslint-disable-next-line local/no-as-any -- terminal_status is a string enum; Select returns string and the update fn accepts the wider type
                  onValueChange={(v) => onUpdate(node.id, { terminal_status: v as any })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="What happens to parts here?" />
                  </SelectTrigger>
                  <SelectContent>
                    {TERMINAL_STATUS_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Badge variant={
                  data.terminalStatus === 'COMPLETED' || data.terminalStatus === 'SHIPPED'
                    ? 'default'
                    : data.terminalStatus === 'SCRAPPED'
                      ? 'destructive'
                      : 'secondary'
                }>
                  {data.terminalStatus?.replace('_', ' ') || 'Not set'}
                </Badge>
              )}
            </div>
          </>
        )}

        {/* REWORK steps: the visit limit is the defining setting. */}
        {isReworkType && (
          <>
            <Separator />
            <div className="space-y-1.5">
              <Label htmlFor="max-visits">Max visits before escalation</Label>
              {editable ? (
                <Input
                  id="max-visits"
                  type="number"
                  min={1}
                  value={data.maxVisits || ''}
                  onChange={(e) => onUpdate(node.id, { max_visits: e.target.value ? parseInt(e.target.value) : null })}
                  placeholder="Unlimited"
                />
              ) : (
                <p className="text-sm">{data.maxVisits || 'Unlimited'}</p>
              )}
            </div>
          </>
        )}

        {/* TIMER steps: the expected duration is the defining setting. */}
        {isTimerType && (
          <>
            <Separator />
            <div className="space-y-1.5">
              <Label htmlFor="expected-duration">Expected duration</Label>
              {editable ? (
                <DurationInput
                  value={data.expectedDuration ? parseDurationToMinutes(data.expectedDuration) as number : null}
                  onChange={(minutes) => {
                    const duration = minutes ? formatMinutesToDuration(minutes) : null;
                    onUpdate(node.id, { expected_duration: duration });
                  }}
                  placeholder="HH:MM:SS"
                />
              ) : (
                <p className="text-sm">{data.expectedDuration ? formatDurationDisplay(data.expectedDuration) : 'Not set'}</p>
              )}
            </div>
          </>
        )}

        {/* RECEIVING step: an outside-process (subcontract) node owns the whole
            step — send parts out to a vendor, receive them back, inspect on return.
            The flag + vendor turn this receiving node into that OSP operation. */}
        {isReceivingType && (
          <>
            <Separator />
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="is-osp" className="text-sm font-normal">Outside process (subcontract)</Label>
                  <p className="text-xs text-muted-foreground">
                    Parts are sent to a vendor (heat treat, plating…) and inspected on return.
                  </p>
                </div>
                {editable ? (
                  <Switch
                    id="is-osp"
                    checked={data.isOutsideProcess || false}
                    onCheckedChange={(checked) => onUpdate(node.id, { is_outside_process: checked })}
                  />
                ) : (
                  <Badge variant={data.isOutsideProcess ? 'default' : 'secondary'}>
                    {data.isOutsideProcess ? 'Yes' : 'No'}
                  </Badge>
                )}
              </div>

              {data.isOutsideProcess && (
                <div className="space-y-1.5">
                  <Label className="text-sm font-normal">Default vendor</Label>
                  {editable ? (
                    <Select
                      value={data.outsideSupplier || ''}
                      onValueChange={(v) => onUpdate(node.id, { outside_supplier: v })}
                    >
                      <SelectTrigger><SelectValue placeholder="Choose a subcontract vendor…" /></SelectTrigger>
                      <SelectContent>
                        {companies.map((c) => (
                          <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Badge variant="outline">{data.outsideSupplierName || 'Not set'}</Badge>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Overridable per shipment when parts are sent out.
                  </p>
                </div>
              )}
            </div>
          </>
        )}

        {/* Configuration shortcuts — measurements/sampling/docs/substeps. Only
            on working steps (not Start/Terminal). */}
        {showConfiguration && (
          <>
            <Separator />
            <div className="space-y-3">
              <Label className="text-sm font-medium">Configuration</Label>

              {/* Measurements */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm">
                  <Ruler className="h-4 w-4 text-muted-foreground" />
                  <span>Measurements</span>
                  {measurementCount > 0 && (
                    <Badge variant="secondary" className="text-xs">{measurementCount}</Badge>
                  )}
                </div>
                {stepId && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => setMeasurementsOpen(true)}
                    title={editable ? "Configure measurements" : "View measurements"}
                  >
                    {editable ? <Settings className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                )}
              </div>

              {/* Sampling Rules */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm">
                  <Target className="h-4 w-4 text-muted-foreground" />
                  <span>Sampling Rules</span>
                  {samplingRuleCount > 0 && (
                    <Badge variant="secondary" className="text-xs">{samplingRuleCount}</Badge>
                  )}
                </div>
                {stepId && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => setSamplingOpen(true)}
                    title={editable ? "Configure sampling rules" : "View sampling rules"}
                  >
                    {editable ? <Settings className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                )}
              </div>

              {/* Documents */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <span>Documents</span>
                  {documentCount > 0 && (
                    <Badge variant="secondary" className="text-xs">{documentCount}</Badge>
                  )}
                </div>
                {stepId && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => setDocumentsOpen(true)}
                    title={editable ? "Configure documents" : "View documents"}
                  >
                    {editable ? <Settings className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                )}
              </div>

              {/* Substeps — drill-down into the DWI substep editor. Disabled
                  until the step is persisted (needs a real stepId in the URL). */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm">
                  <ListChecks className="h-4 w-4 text-muted-foreground" />
                  <span>Substeps</span>
                  {substepCount > 0 && (
                    <Badge variant="secondary" className="text-xs">{substepCount}</Badge>
                  )}
                </div>
                {stepId && processId && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() =>
                      navigate({
                        to: '/editor/processes/$processId/steps/$stepId/substeps',
                        params: { processId, stepId },
                      })
                    }
                    title={editable ? 'Edit substeps' : 'View substeps'}
                  >
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                )}
              </div>

              {!stepId && editable && (
                <p className="text-xs text-muted-foreground">
                  Save process to configure measurements, sampling, documents, and substeps
                </p>
              )}
            </div>
          </>
        )}

        {/* Advanced — secondary/occasional settings, collapsed by default so the
            common case stays short. Includes type-overrides (mark any step as a
            decision/terminal), duration, rework limit, QA flags, FPI, batch. */}
        <Separator />
        <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
          <CollapsibleTrigger className="flex w-full items-center justify-between text-sm font-medium text-muted-foreground hover:text-foreground">
            <span>Advanced</span>
            <ChevronDown className={`h-4 w-4 transition-transform ${advancedOpen ? 'rotate-180' : ''}`} />
          </CollapsibleTrigger>
          <CollapsibleContent className="space-y-4 pt-3">
            {/* Promote a non-decision step to a decision (decision nodes are
                already decisions, so the toggle is hidden for them). */}
            {!isDecisionType && (
              <div className="flex items-center justify-between">
                <Label htmlFor="is-decision" className="text-sm font-normal">Decision point</Label>
                {editable ? (
                  <Switch
                    id="is-decision"
                    checked={data.isDecisionPoint || false}
                    onCheckedChange={(checked) => onUpdate(node.id, { is_decision_point: checked })}
                  />
                ) : (
                  <Badge variant={data.isDecisionPoint ? 'default' : 'secondary'}>
                    {data.isDecisionPoint ? 'Yes' : 'No'}
                  </Badge>
                )}
              </div>
            )}

            {/* Mark a non-terminal step terminal (terminal nodes are already). */}
            {!isTerminalType && (
              <div className="flex items-center justify-between">
                <Label htmlFor="is-terminal" className="text-sm font-normal">Terminal step</Label>
                {editable ? (
                  <Switch
                    id="is-terminal"
                    checked={data.isTerminal || false}
                    onCheckedChange={(checked) => onUpdate(node.id, { is_terminal: checked })}
                  />
                ) : (
                  <Badge variant={data.isTerminal ? 'default' : 'secondary'}>
                    {data.isTerminal ? 'Yes' : 'No'}
                  </Badge>
                )}
              </div>
            )}

            {/* Expected duration (core field for TIMER, advanced elsewhere). */}
            {!isTimerType && (
              <div className="space-y-1.5">
                <Label htmlFor="expected-duration-adv" className="text-sm font-normal">Expected duration</Label>
                {editable ? (
                  <DurationInput
                    value={data.expectedDuration ? parseDurationToMinutes(data.expectedDuration) as number : null}
                    onChange={(minutes) => {
                      const duration = minutes ? formatMinutesToDuration(minutes) : null;
                      onUpdate(node.id, { expected_duration: duration });
                    }}
                    placeholder="HH:MM:SS"
                  />
                ) : (
                  <p className="text-sm">{data.expectedDuration ? formatDurationDisplay(data.expectedDuration) : 'Not set'}</p>
                )}
              </div>
            )}

            {/* Rework/visit limit (core field for REWORK, advanced elsewhere). */}
            {!isReworkType && (
              <div className="space-y-1.5">
                <Label htmlFor="max-visits-adv" className="text-sm font-normal">Max visits (rework limit)</Label>
                {editable ? (
                  <Input
                    id="max-visits-adv"
                    type="number"
                    min={1}
                    value={data.maxVisits || ''}
                    onChange={(e) => onUpdate(node.id, { max_visits: e.target.value ? parseInt(e.target.value) : null })}
                    placeholder="Unlimited"
                  />
                ) : (
                  <p className="text-sm">{data.maxVisits || 'Unlimited'}</p>
                )}
              </div>
            )}

            {/* QA flags */}
            <div className="flex items-center justify-between">
              <Label htmlFor="requires-qa" className="text-sm font-normal">Requires QA signoff</Label>
              {editable ? (
                <Switch
                  id="requires-qa"
                  checked={data.requiresQaSignoff || false}
                  onCheckedChange={(checked) => onUpdate(node.id, { requires_qa_signoff: checked })}
                />
              ) : (
                <Badge variant={data.requiresQaSignoff ? 'default' : 'secondary'}>
                  {data.requiresQaSignoff ? 'Yes' : 'No'}
                </Badge>
              )}
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="sampling-required" className="text-sm font-normal">Sampling required</Label>
              {editable ? (
                <Switch
                  id="sampling-required"
                  checked={data.samplingRequired || false}
                  onCheckedChange={(checked) => onUpdate(node.id, { sampling_required: checked })}
                />
              ) : (
                <Badge variant={data.samplingRequired ? 'default' : 'secondary'}>
                  {data.samplingRequired ? 'Yes' : 'No'}
                </Badge>
              )}
            </div>

            {(data.samplingRequired || data.minSamplingRate > 0) && (
              <div className="space-y-1.5">
                <Label htmlFor="sampling-rate" className="text-sm font-normal">Min sampling rate (%)</Label>
                {editable ? (
                  <Input
                    id="sampling-rate"
                    type="number"
                    min={0}
                    max={100}
                    value={data.minSamplingRate || ''}
                    onChange={(e) => onUpdate(node.id, { min_sampling_rate: e.target.value ? parseInt(e.target.value) : undefined })}
                    placeholder="e.g., 10"
                  />
                ) : (
                  <p className="text-sm">{data.minSamplingRate ? `${data.minSamplingRate}%` : 'Not set'}</p>
                )}
              </div>
            )}

            {/* First Piece Inspection */}
            <div className="flex items-center justify-between">
              <Label htmlFor="requires-fpi" className="text-sm font-normal">Requires first-piece inspection</Label>
              {editable ? (
                <Switch
                  id="requires-fpi"
                  checked={data.requiresFirstPieceInspection || false}
                  onCheckedChange={(checked) => onUpdate(node.id, { requires_first_piece_inspection: checked })}
                />
              ) : (
                <Badge variant={data.requiresFirstPieceInspection ? 'default' : 'secondary'}>
                  {data.requiresFirstPieceInspection ? 'Yes' : 'No'}
                </Badge>
              )}
            </div>

            {data.requiresFirstPieceInspection && editable && (
              <div className="space-y-1.5">
                <Label htmlFor="fpi-scope" className="text-sm font-normal">FPI scope</Label>
                <Select value={data.fpiScope || 'PER_WORKORDER'} onValueChange={(v) => onUpdate(node.id, { fpi_scope: v })}>
                  <SelectTrigger id="fpi-scope"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {FPI_SCOPE_OPTIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Batch completion */}
            <div className="flex items-center justify-between">
              <Label htmlFor="requires-batch" className="text-sm font-normal">Move lot as a unit</Label>
              {editable ? (
                <Switch
                  id="requires-batch"
                  checked={data.requiresBatchCompletion || false}
                  onCheckedChange={(checked) => onUpdate(node.id, { requires_batch_completion: checked })}
                />
              ) : (
                <Badge variant={data.requiresBatchCompletion ? 'default' : 'secondary'}>
                  {data.requiresBatchCompletion ? 'Yes' : 'No'}
                </Badge>
              )}
            </div>

            {data.requiresBatchCompletion && (
              <div className="space-y-1.5">
                <Label htmlFor="batch-ready-threshold" className="text-sm font-normal">Batch ready threshold (% of lot ready to advance)</Label>
                {editable ? (
                  <Input
                    id="batch-ready-threshold"
                    type="number"
                    min={0}
                    max={100}
                    value={data.passThreshold != null ? Math.round(data.passThreshold * 100) : ''}
                    onChange={(e) => onUpdate(node.id, { pass_threshold: e.target.value ? parseInt(e.target.value) / 100 : undefined })}
                    placeholder="100"
                  />
                ) : (
                  <p className="text-sm">{data.passThreshold != null ? `${Math.round(data.passThreshold * 100)}%` : '100%'}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Fraction of the lot that must be READY before the batch advances — not a pass/fail threshold.
                </p>
              </div>
            )}
          </CollapsibleContent>
        </Collapsible>

        {/* Editor Dialogs */}
        {stepId && (
          <>
            <MeasurementsEditor
              stepId={stepId}
              stepName={data.label || 'Step'}
              open={measurementsOpen}
              onOpenChange={setMeasurementsOpen}
              readOnly={!editable}
            />
            <StepSamplingEditor
              stepId={stepId}
              stepName={data.label || 'Step'}
              open={samplingOpen}
              onOpenChange={setSamplingOpen}
              readOnly={!editable}
            />
            <StepDocumentsEditor
              stepId={stepId}
              stepName={data.label || 'Step'}
              open={documentsOpen}
              onOpenChange={setDocumentsOpen}
              readOnly={!editable}
            />
          </>
        )}

        {editable && (
          <>
            <Separator />
            <Button
              variant="destructive"
              size="sm"
              className="w-full"
              onClick={() => onDelete(node.id)}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Step
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}
