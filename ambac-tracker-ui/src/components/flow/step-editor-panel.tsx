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
import { DurationInput } from '@/components/ui/duration-input';
import { Trash2, X, Ruler, Target, Settings, FileText, Eye } from 'lucide-react';
import type { StepData } from './use-steps-to-flow';
import { useRetrieveMeasurementDefinitions } from '@/hooks/useRetrieveMeasurementDefinitions';
import { useRetrieveStepWithSamplingRules } from '@/hooks/useRetrieveStepWithSamplingRules';
import { useRetrieveDocuments } from '@/hooks/useRetrieveDocuments';
import { useContentTypeMapping } from '@/hooks/useContentTypes';
import { MeasurementsEditor } from './measurements-editor';
import { StepSamplingEditor } from './step-sampling-editor';
import { StepDocumentsEditor } from './step-documents-editor';
import { parseDurationToMinutes, formatMinutesToDuration, formatDurationDisplay } from '@/lib/duration-utils';

/** Terminal status options */
export const TERMINAL_STATUS_OPTIONS = [
  { value: 'completed', label: 'Completed Successfully' },
  { value: 'shipped', label: 'Shipped to Customer' },
  { value: 'stock', label: 'Put into Inventory' },
  { value: 'scrapped', label: 'Scrapped' },
  { value: 'returned', label: 'Returned to Supplier' },
  { value: 'awaiting_pickup', label: 'Awaiting Customer Pickup' },
  { value: 'core_banked', label: 'Core Banked' },
  { value: 'rma_closed', label: 'RMA Closed' },
] as const;

/** Decision type options */
export const DECISION_TYPE_OPTIONS = [
  { value: 'qa_result', label: 'Based on QA Pass/Fail' },
  { value: 'measurement', label: 'Based on Measurement Threshold' },
  { value: 'manual', label: 'Manual Operator Selection' },
] as const;

export interface StepEditorPanelProps {
  node: Node;
  onUpdate: (nodeId: string, data: Partial<StepData>) => void;
  onDelete: (nodeId: string) => void;
  onClose?: () => void;
  editable: boolean;
}

export function StepEditorPanel({ node, onUpdate, onDelete, onClose, editable }: StepEditorPanelProps) {
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
    { queries: { step: stepId } },
    { enabled: !!stepId }
  );
  const measurementCount = measurementsResponse?.count ?? 0;

  // Fetch sampling rules count
  const { data: stepWithRules } = useRetrieveStepWithSamplingRules(
    { params: { id: stepId! } },
    { enabled: !!stepId }
  );
  // active_ruleset may be on the extended type from the hook
  const samplingRuleCount = (stepWithRules as any)?.active_ruleset?.rules?.length ?? 0;

  // Fetch document count
  const { data: documentsResponse } = useRetrieveDocuments(
    {
      content_type: stepsContentTypeId,
      object_id: stepId,
    },
    { enabled: !!stepId && !!stepsContentTypeId && !contentTypesLoading }
  );
  const documentCount = documentsResponse?.count ?? 0;

  return (
    <Card className="w-80 shrink-0 overflow-auto max-h-full">
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

        <Separator />

        {/* Decision Point Settings */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label htmlFor="is-decision">Decision Point</Label>
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

          {data.isDecisionPoint && (
            <div className="space-y-1.5">
              <Label>Decision Type</Label>
              {editable ? (
                <Select
                  value={data.decisionType || ''}
                  onValueChange={(v) => onUpdate(node.id, { decision_type: v as any })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type..." />
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
          )}
        </div>

        <Separator />

        {/* Terminal Settings */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label htmlFor="is-terminal">Terminal Step</Label>
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

          {data.isTerminal && (
            <div className="space-y-1.5">
              <Label>Terminal Status</Label>
              {editable ? (
                <Select
                  value={data.terminalStatus || ''}
                  onValueChange={(v) => onUpdate(node.id, { terminal_status: v as any })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select status..." />
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
                  data.terminalStatus === 'completed' || data.terminalStatus === 'shipped'
                    ? 'default'
                    : data.terminalStatus === 'scrapped'
                      ? 'destructive'
                      : 'secondary'
                }>
                  {data.terminalStatus?.replace('_', ' ') || 'Not set'}
                </Badge>
              )}
            </div>
          )}
        </div>

        <Separator />

        {/* Rework/Cycle Control */}
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="max-visits">Max Visits (Rework Limit)</Label>
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

          <div className="space-y-1.5">
            <Label htmlFor="expected-duration">Expected Duration</Label>
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
        </div>

        <Separator />

        {/* QA Settings */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">QA Settings</Label>

          <div className="flex items-center justify-between">
            <Label htmlFor="requires-qa" className="text-sm font-normal">Requires QA Signoff</Label>
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
            <Label htmlFor="sampling-required" className="text-sm font-normal">Sampling Required</Label>
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
              <Label htmlFor="sampling-rate">Min Sampling Rate (%)</Label>
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
        </div>

        <Separator />

        {/* Measurement & Sampling Configuration */}
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

          {!stepId && editable && (
            <p className="text-xs text-muted-foreground">
              Save process to configure measurements, sampling, and documents
            </p>
          )}
        </div>

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
