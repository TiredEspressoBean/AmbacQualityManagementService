"use client";

import { useEffect, useMemo } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Target, Loader2, ArrowRight, TrendingUp, AlertTriangle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useRetrieveStepWithSamplingRules } from '@/hooks/useRetrieveStepWithSamplingRules';
import { useRetrieveMeasurementDefinitions } from '@/hooks/useRetrieveMeasurementDefinitions';
import { useUpdateStepSamplingRules } from '@/hooks/useUpdateStepSamplingRules';
import { useRetrieveApprovalTemplates } from '@/hooks/useRetrieveApprovalTemplates';
import SamplingRulesEditor from '@/components/SamplingRulesEditor';
import { toast } from 'sonner';

const samplingRuleSchema = z.object({
  rule_type: z.string().min(1),
  value: z.union([z.string(), z.number(), z.null()]),
  order: z.number().min(0),
});

const formSchema = z.object({
  // Sampling family — the discriminator. Streaming stacks per-part rules; lot
  // acceptance is a single AQL/C=0 attribute plan; variables is a Z1.9 plan that
  // measures one characteristic. (Continuous reserved.)
  family: z.enum(['STREAMING', 'LOT_ACCEPTANCE', 'VARIABLES']).optional(),
  rules: z.array(samplingRuleSchema),
  fallback_rules: z.array(samplingRuleSchema).optional(),
  tighten_after: z.number().nullable().optional(),
  fallback_duration: z.number().nullable().optional(),
  // Acceptance sampling (RECEIVING steps)
  strategy: z.string().optional(),
  aql: z.union([z.string(), z.number(), z.null()]).optional(),
  inspection_level: z.string().optional(),
  severity: z.string().optional(),
  // Variables (Z1.9): the single numeric characteristic the plan measures.
  variables_characteristic: z.string().nullable().optional(),
  // Quality gate
  gate_metric: z.string().optional(),
  gate_threshold: z.union([z.string(), z.number(), z.null()]).optional(),
  gate_window: z.string().optional(),
  gate_window_n: z.number().nullable().optional(),
  gate_min_sample: z.number().nullable().optional(),
  gate_actions: z.array(z.string()).optional(),
  gate_capa_type: z.string().optional(),
  gate_capa_severity: z.string().optional(),
  gate_approval_template: z.string().nullable().optional(),
});

const NONE = '__none__';

// Standard AQL series (ANSI/ASQ Z1.4 / ISO 2859-1). Off-series values have no
// table row, so AQL is a fixed selection rather than free entry.
const AQL_SERIES = ['0.010', '0.015', '0.025', '0.040', '0.065', '0.10', '0.15',
  '0.25', '0.40', '0.65', '1.0', '1.5', '2.5', '4.0', '6.5', '10'];

// Gate actions are side-effects only — things that DON'T move the subject through
// the flow. Anything spatial (quarantine, scrap, rework, return-to-supplier, next)
// is a destination node reached by an edge, driven by the step's decision type, not
// a gate action. Tightening is owned by each family's Escalation section. So the gate
// triggers only: raise a parallel quality record, or require a signoff.
const GATE_ACTIONS = [
  { value: 'RAISE_CAPA_SCAR', label: 'Raise CAPA / SCAR' },
  { value: 'REQUIRE_APPROVAL', label: 'Require approval' },
];

type FormValues = z.infer<typeof formSchema>;
type Family = NonNullable<FormValues['family']>;

type SamplingRule = {
  rule_type: string;
  value: string | number | null | undefined;
  order?: number;
};

/** Parse a value that could be string, number, null, or undefined */
function parseRuleValue(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === '') return null;
  const num = typeof value === 'string' ? parseFloat(value) : Number(value);
  return isNaN(num) ? null : num;
}

type CoverageEstimate = {
  percentage: number;
  fixedCount: number;
  is100Percent: boolean;
};

/** Calculate coverage data from rules */
function calculateCoverage(rules: SamplingRule[]): CoverageEstimate {
  if (!rules || rules.length === 0) {
    return { percentage: 0, fixedCount: 0, is100Percent: false };
  }

  let maxPercentage = 0;
  let fixedCount = 0;

  for (const rule of rules) {
    const value = parseRuleValue(rule.value);
    const ruleType = rule.rule_type?.toLowerCase();

    switch (ruleType) {
      case "all":
        return { percentage: 100, fixedCount: 0, is100Percent: true };
      case "none":
        break;
      case "percentage":
        if (value !== null && value > 0) {
          maxPercentage = Math.max(maxPercentage, value);
        }
        break;
      case "every_nth":
      case "every_nth_part":
        if (value !== null && value > 0) {
          maxPercentage = Math.max(maxPercentage, 100 / value);
        }
        break;
      case "first_n":
      case "first_n_parts":
        if (value !== null && value > 0) {
          fixedCount += value;
        }
        break;
      case "last_n":
      case "last_n_parts":
        if (value !== null && value > 0) {
          fixedCount += value;
        }
        break;
      case "first_and_last":
        fixedCount += 2;
        break;
      case "random":
      case "random_within_n":
        if (value !== null && value > 0) {
          maxPercentage = Math.max(maxPercentage, value);
        } else {
          maxPercentage = Math.max(maxPercentage, 10);
        }
        break;
    }
  }

  return { percentage: maxPercentage, fixedCount, is100Percent: false };
}

/** Format coverage estimate for display */
function formatCoverage(coverage: CoverageEstimate): string {
  if (coverage.is100Percent) return "100%";

  const parts: string[] = [];

  if (coverage.percentage > 0) {
    if (coverage.percentage >= 100) return "100%";
    parts.push(coverage.percentage < 1
      ? `~${coverage.percentage.toFixed(1)}%`
      : `~${Math.round(coverage.percentage)}%`);
  }

  if (coverage.fixedCount > 0) {
    parts.push(`+${coverage.fixedCount} parts`);
  }

  if (parts.length === 0) return "0%";
  return parts.join(" ");
}

/** Combine two coverage estimates (additive) */
function combineCoverage(primary: CoverageEstimate, escalation: CoverageEstimate): CoverageEstimate {
  if (primary.is100Percent || escalation.is100Percent) {
    return { percentage: 100, fixedCount: 0, is100Percent: true };
  }

  // Percentages don't simply add (overlap possible), but for display we show combined
  const combinedPercentage = Math.min(100, primary.percentage + escalation.percentage);
  const combinedFixed = primary.fixedCount + escalation.fixedCount;

  return {
    percentage: combinedPercentage,
    fixedCount: combinedFixed,
    is100Percent: combinedPercentage >= 100,
  };
}

/** Rules that require a value */
const rulesRequiringValue = new Set([
  'every_nth_part', 'every_nth',
  'percentage',
  'first_n_parts', 'first_n',
  'last_n_parts', 'last_n',
  'random_within_n',
]);

type ValidationWarning = {
  type: 'error' | 'warning';
  message: string;
};

/** Validate sampling configuration */
function validateSamplingConfig(
  rules: SamplingRule[],
  fallbackRules: SamplingRule[],
  threshold: number | null | undefined,
  duration: number | null | undefined
): ValidationWarning[] {
  const warnings: ValidationWarning[] = [];

  // Check for empty primary rules
  if (rules.length === 0) {
    warnings.push({
      type: 'warning',
      message: 'No primary sampling rules defined. Parts will not be sampled at this step.',
    });
  }

  // Check for rules missing required values
  for (const rule of rules) {
    const ruleType = rule.rule_type?.toLowerCase();
    if (rulesRequiringValue.has(ruleType) && (rule.value === null || rule.value === undefined)) {
      warnings.push({
        type: 'error',
        message: `Rule "${rule.rule_type}" requires a value.`,
      });
    }
    // Check for invalid percentage values
    if (ruleType === 'percentage') {
      const val = parseRuleValue(rule.value);
      if (val !== null && (val < 0 || val > 100)) {
        warnings.push({
          type: 'error',
          message: `Percentage must be between 0 and 100 (got ${val}).`,
        });
      }
    }
  }

  // Check escalation configuration
  if (fallbackRules.length > 0) {
    if (threshold === null || threshold === undefined) {
      warnings.push({
        type: 'warning',
        message: 'Escalation rules defined but trigger threshold not set. Rules won\'t activate automatically.',
      });
    }
    if (duration === null || duration === undefined) {
      warnings.push({
        type: 'warning',
        message: 'Escalation rules defined but recovery duration not set. Rules won\'t de-escalate automatically.',
      });
    }

    // Check fallback rules for missing values
    for (const rule of fallbackRules) {
      const ruleType = rule.rule_type?.toLowerCase();
      if (rulesRequiringValue.has(ruleType) && (rule.value === null || rule.value === undefined)) {
        warnings.push({
          type: 'error',
          message: `Escalation rule "${rule.rule_type}" requires a value.`,
        });
      }
    }
  }

  return warnings;
}

export interface StepSamplingEditorProps {
  stepId: string;
  stepName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  readOnly?: boolean;
}

export function StepSamplingEditor({ stepId, stepName, open, onOpenChange, readOnly = false }: StepSamplingEditorProps) {
  const { data: step, isLoading, refetch } = useRetrieveStepWithSamplingRules(
    { params: { id: stepId } },
    { enabled: open }
  );
  const updateSamplingRules = useUpdateStepSamplingRules();
  const { data: approvalTemplates } = useRetrieveApprovalTemplates({ limit: 200 } as never);
  // Numeric measurement definitions on this step — the candidates a Z1.9 variables
  // plan can measure (variables works on one numeric characteristic at a time).
  const { data: measurementsResp } = useRetrieveMeasurementDefinitions(
    { step: stepId }, undefined, { enabled: open });
  // eslint-disable-next-line local/no-as-any -- MeasurementDefinition list rows; we read id/label/type
  const numericChars = ((measurementsResp?.results ?? []) as any[]).filter((m) => m.type === 'NUMERIC');

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      family: 'STREAMING',
      rules: [],
      fallback_rules: [],
      tighten_after: null,
      fallback_duration: null,
      gate_actions: [],
    },
  });

  // Populate form when step data loads
  // Note: active_ruleset and fallback_ruleset come from extended step type via hook
  useEffect(() => {
    if (step && open) {
      // eslint-disable-next-line local/no-as-any -- step schema doesn't include ruleset fields; they're populated by a separate endpoint at runtime
      const stepWithRules = step as any;
      const ar = stepWithRules.active_ruleset ?? {};
      // Infer the family from existing data. A Z19 strategy / VARIABLES rule /
      // variables_characteristic means variables; a strategy / AQL / AQL|C_ZERO
      // rule means attribute lot acceptance; otherwise per-part streaming.
      const isVariables = ar.strategy === 'Z19' || !!ar.variables_characteristic ||
        (ar.rules ?? []).some((r: { rule_type?: string }) => r.rule_type === 'VARIABLES');
      const isLot = !isVariables && !!(ar.strategy || ar.aql ||
        (ar.rules ?? []).some((r: { rule_type?: string }) => r.rule_type === 'AQL' || r.rule_type === 'C_ZERO'));
      form.reset({
        family: isVariables ? 'VARIABLES' : isLot ? 'LOT_ACCEPTANCE' : 'STREAMING',
        rules: ar.rules ?? [],
        fallback_rules: stepWithRules.fallback_ruleset?.rules ?? [],
        tighten_after: ar.tighten_after ?? null,
        fallback_duration: ar.fallback_duration ?? null,
        strategy: ar.strategy ?? '',
        aql: ar.aql ?? null,
        inspection_level: ar.inspection_level ?? '',
        severity: ar.severity ?? '',
        variables_characteristic: ar.variables_characteristic ?? null,
        gate_metric: ar.gate_metric ?? '',
        gate_threshold: ar.gate_threshold ?? null,
        gate_window: ar.gate_window ?? '',
        gate_window_n: ar.gate_window_n ?? null,
        gate_min_sample: ar.gate_min_sample ?? null,
        gate_actions: ar.gate_actions ?? [],
        gate_capa_type: ar.gate_capa_type ?? '',
        gate_capa_severity: ar.gate_capa_severity ?? '',
        gate_approval_template: ar.gate_approval_template ?? null,
      });
    }
  }, [step, open, form]);

  const normalizeRules = (
    rules: { rule_type: string; value: string | number | null | undefined }[]
  ): { rule_type: string; value: string | number | null; order: number }[] => {
    return rules.map((rule, index) => ({
      rule_type: rule.rule_type,
      value: rule.value ?? null,
      order: index + 1,
    }));
  };

  const changeFamily = (v: Family) => {
    form.setValue('family', v);
    if (v === 'STREAMING') {
      form.setValue('strategy', '');
      form.setValue('aql', null);
      form.setValue('inspection_level', '');
      form.setValue('severity', '');
      form.setValue('variables_characteristic', null);
      return;
    }
    // Acceptance families (lot attribute + variables): streaming concepts don't apply.
    form.setValue('rules', []);
    form.setValue('fallback_rules', []);
    form.setValue('tighten_after', null);
    form.setValue('fallback_duration', null);
    if (v === 'VARIABLES') {
      form.setValue('strategy', 'Z19');
      form.setValue('severity', '');
    } else { // LOT_ACCEPTANCE (attribute)
      form.setValue('variables_characteristic', null);
      const s = form.getValues('strategy');
      if (!s || s === 'Z19') form.setValue('strategy', 'C0');
    }
  };

  const handleSubmit = (values: FormValues) => {
    const family = values.family ?? 'STREAMING';
    const isLot = family === 'LOT_ACCEPTANCE';
    const isVar = family === 'VARIABLES';
    const isAcceptance = isLot || isVar;
    // Acceptance families persist a single marker rule (the strategy) + plan params;
    // streaming persists its per-part rule rows. They never coexist.
    const markerRule = isVar
      ? [{ rule_type: 'VARIABLES', value: null, order: 1 }]
      : [{ rule_type: values.strategy === 'Z14' ? 'AQL' : 'C_ZERO', value: null, order: 1 }];

    updateSamplingRules.mutate(
      {
        id: stepId,
        data: {
          // eslint-disable-next-line local/no-as-any -- rule shapes are looser than the generated tuple/enum types
          rules: (isAcceptance ? markerRule : normalizeRules(values.rules)) as any,
          // eslint-disable-next-line local/no-as-any -- same
          fallback_rules: (isAcceptance ? [] : normalizeRules(values.fallback_rules ?? [])) as any,
          tighten_after: isAcceptance ? null : (values.tighten_after ?? undefined),
          // fallback_duration is optional-but-non-nullable in the schema — omit
          // (undefined) rather than send null for acceptance families.
          fallback_duration: isAcceptance ? undefined : (values.fallback_duration ?? undefined),
          // Acceptance plan. Attribute (Lot): C0/Z14, AQL, level/severity (Z14 only).
          // Variables: strategy Z19, AQL + level, the measured characteristic, no severity (MVP).
          strategy: isVar ? 'Z19' : isLot ? (values.strategy || 'C0') : '',
          aql: isAcceptance ? (values.aql ?? null) : null,
          inspection_level: isVar
            ? (values.inspection_level || 'II')
            : isLot ? (values.strategy === 'Z14' ? (values.inspection_level || 'II') : 'II') : '',
          severity: isLot ? (values.strategy === 'Z14' ? (values.severity || '') : '') : '',
          // eslint-disable-next-line local/no-as-any -- variables_characteristic is on the update serializer; generated type may lag
          variables_characteristic: (isVar ? (values.variables_characteristic ?? null) : null) as any,
          // Quality gate — applies to both families.
          gate_metric: values.gate_metric || '',
          gate_threshold: values.gate_threshold ?? null,
          gate_window: values.gate_window || '',
          gate_window_n: values.gate_window_n ?? null,
          gate_min_sample: values.gate_min_sample ?? null,
          gate_actions: values.gate_actions ?? [],
          gate_capa_type: values.gate_capa_type || '',
          gate_capa_severity: values.gate_capa_severity || '',
          gate_approval_template: values.gate_approval_template ?? null,
        } as any,
      },
      {
        onSuccess: () => {
          toast.success('Sampling rules updated');
          refetch();
          onOpenChange(false);
        },
        onError: (err) => {
          console.error('Failed to update sampling rules:', err);
          toast.error('Failed to update sampling rules');
        },
      }
    );
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      form.reset();
    }
    onOpenChange(newOpen);
  };

  const watchedRulesRaw = form.watch('rules');
  const watchedRules = useMemo(() => watchedRulesRaw ?? [], [watchedRulesRaw]);
  const watchedFallbackRulesRaw = form.watch('fallback_rules');
  const watchedFallbackRules = useMemo(() => watchedFallbackRulesRaw ?? [], [watchedFallbackRulesRaw]);
  const watchedThreshold = form.watch('tighten_after');
  const watchedDuration = form.watch('fallback_duration');
  const watchedFamily = form.watch('family') ?? 'STREAMING';
  const hasFallbackRules = watchedFallbackRules.length > 0;

  // Calculate coverage estimates
  const primaryCoverage = useMemo(
    () => calculateCoverage(watchedRules as SamplingRule[]),
    [watchedRules]
  );
  const escalationCoverage = useMemo(
    () => calculateCoverage(watchedFallbackRules as SamplingRule[]),
    [watchedFallbackRules]
  );
  const combinedCoverage = useMemo(
    () => combineCoverage(primaryCoverage, escalationCoverage),
    [primaryCoverage, escalationCoverage]
  );

  // Format for display
  const primaryDisplay = formatCoverage(primaryCoverage);
  const escalationDisplay = formatCoverage(escalationCoverage);
  const combinedDisplay = formatCoverage(combinedCoverage);

  // Validate configuration
  const validationWarnings = useMemo(
    () => validateSamplingConfig(
      watchedRules as SamplingRule[],
      watchedFallbackRules as SamplingRule[],
      watchedThreshold,
      watchedDuration
    ),
    [watchedRules, watchedFallbackRules, watchedThreshold, watchedDuration]
  );

  const hasErrors = watchedFamily === 'STREAMING' && validationWarnings.some(w => w.type === 'error');

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] p-0 gap-0">
        <DialogHeader className="p-6 pb-0">
          <DialogTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Sampling — "{stepName}"
          </DialogTitle>
          <DialogDescription>
            Choose the sampling method for this step and configure its rules, plan, and gate.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[calc(85vh-8rem)]">
          <div className="p-6 pt-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <FormProvider {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
              {/* Sampling method (family discriminator) */}
              <div className="space-y-1.5">
                <Label className="text-sm font-medium">Sampling method</Label>
                <Select value={watchedFamily} onValueChange={(v) => changeFamily(v as Family)} disabled={readOnly}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="STREAMING">Per-part streaming</SelectItem>
                    <SelectItem value="LOT_ACCEPTANCE">Lot acceptance — attribute</SelectItem>
                    <SelectItem value="VARIABLES">Variables (measured)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {watchedFamily === 'VARIABLES'
                    ? 'Measure one characteristic on the sample; accept on the spread (x̄/s) vs the constant k (ANSI/ASQ Z1.9).'
                    : watchedFamily === 'LOT_ACCEPTANCE'
                      ? 'Accept or reject a whole lot from a sample (n / Ac / Re). The scheme (C=0 / Z1.4) is set below.'
                      : 'Select individual parts from the flow to inspect (every-Nth, %, …).'}
                </p>
              </div>

              {watchedFamily === 'STREAMING' && (<>
              {/* Summary Card */}
              <Card className="bg-muted/30">
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between">
                    {/* Primary Rate */}
                    <div className="text-center">
                      <div className="text-2xl font-bold text-primary">{primaryDisplay}</div>
                      <div className="text-xs text-muted-foreground">Normal Sampling</div>
                    </div>

                    {/* Escalation Flow */}
                    {hasFallbackRules && (
                      <>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <ArrowRight className="h-4 w-4" />
                          <div className="text-center">
                            <div className="font-medium text-foreground">
                              {watchedThreshold ?? '?'} failures
                            </div>
                            <div>triggers</div>
                          </div>
                          <ArrowRight className="h-4 w-4" />
                        </div>

                        {/* Combined Rate (Primary + Escalation) */}
                        <div className="text-center">
                          <div className="text-2xl font-bold text-amber-600">{combinedDisplay}</div>
                          <div className="text-xs text-muted-foreground">
                            Escalated ({primaryDisplay} + {escalationDisplay})
                          </div>
                        </div>

                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <ArrowRight className="h-4 w-4" />
                          <div className="text-center">
                            <div className="font-medium text-foreground">
                              {watchedDuration ?? '?'} passes
                            </div>
                            <div>recovers</div>
                          </div>
                          <ArrowRight className="h-4 w-4" />
                        </div>

                        {/* Back to Primary */}
                        <div className="text-center">
                          <div className="text-2xl font-bold text-primary">{primaryDisplay}</div>
                          <div className="text-xs text-muted-foreground">Normal</div>
                        </div>
                      </>
                    )}

                    {!hasFallbackRules && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <TrendingUp className="h-4 w-4" />
                        <span>Add escalation rules to enable automatic tightening</span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Primary Sampling Rules */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm font-medium">Primary Sampling Rules</Label>
                    <p className="text-sm text-muted-foreground">
                      Rules applied during normal operation
                    </p>
                  </div>
                  <Badge variant="secondary">{primaryDisplay}</Badge>
                </div>
                <SamplingRulesEditor name="rules" label="Primary Rules" readOnly={readOnly} />
              </div>

              <Separator />

              {/* Escalation Rules */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm font-medium">Escalation Rules</Label>
                    <p className="text-sm text-muted-foreground">
                      Tighter sampling triggered by consecutive failures
                    </p>
                  </div>
                  {hasFallbackRules && (
                    <Badge variant="outline" className="text-amber-600 border-amber-600">
                      +{escalationDisplay}
                    </Badge>
                  )}
                </div>
                <SamplingRulesEditor name="fallback_rules" label="Escalation Rules" readOnly={readOnly} />

                {/* Trigger settings - only show when there are escalation rules */}
                {hasFallbackRules && (
                  <div className="flex items-center gap-6 p-4 rounded-lg border bg-muted/30">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="tighten_after" className="text-sm whitespace-nowrap">
                        Escalate after
                      </Label>
                      <Input
                        id="tighten_after"
                        type="number"
                        min={1}
                        disabled={readOnly}
                        className="w-16 h-8"
                        value={watchedThreshold ?? ''}
                        onChange={(e) => {
                          const parsed = parseInt(e.target.value);
                          form.setValue('tighten_after', isNaN(parsed) ? null : parsed);
                        }}
                        placeholder="3"
                      />
                      <span className="text-sm text-muted-foreground">consecutive failures</span>
                    </div>

                    <ArrowRight className="h-4 w-4 text-muted-foreground" />

                    <div className="flex items-center gap-2">
                      <Label htmlFor="fallback_duration" className="text-sm whitespace-nowrap">
                        Return after
                      </Label>
                      <Input
                        id="fallback_duration"
                        type="number"
                        min={1}
                        disabled={readOnly}
                        className="w-16 h-8"
                        value={watchedDuration ?? ''}
                        onChange={(e) => {
                          const parsed = parseInt(e.target.value);
                          form.setValue('fallback_duration', isNaN(parsed) ? null : parsed);
                        }}
                        placeholder="10"
                      />
                      <span className="text-sm text-muted-foreground">consecutive passes</span>
                    </div>
                  </div>
                )}
              </div>
              </>)}

              {watchedFamily === 'LOT_ACCEPTANCE' && (
              <div className="space-y-3">
                <div>
                  <Label className="text-sm font-medium">Acceptance plan</Label>
                  <p className="text-sm text-muted-foreground">
                    Resolves the incoming lot's sample plan (n / Ac / Re) from lot size + these parameters.
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs">Strategy</Label>
                    <Select value={form.watch('strategy') || NONE} onValueChange={(v) => form.setValue('strategy', v === NONE ? '' : v)}>
                      <SelectTrigger className="h-8"><SelectValue placeholder="—" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value={NONE}>—</SelectItem>
                        <SelectItem value="C0">C=0 (Squeglia)</SelectItem>
                        <SelectItem value="Z14">ANSI/ASQ Z1.4</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">AQL</Label>
                    <Select value={(form.watch('aql') as string | null) || NONE} onValueChange={(v) => form.setValue('aql', v === NONE ? null : v)}>
                      <SelectTrigger className="h-8"><SelectValue placeholder="—" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value={NONE}>—</SelectItem>
                        {AQL_SERIES.map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  {/* Inspection level + severity only apply to Z1.4; C=0 (Squeglia)
                      is indexed by AQL + lot size and has no level/severity. */}
                  {form.watch('strategy') === 'Z14' && (
                    <>
                      <div className="space-y-1.5">
                        <Label className="text-xs">Inspection level</Label>
                        <Select value={form.watch('inspection_level') || NONE} onValueChange={(v) => form.setValue('inspection_level', v === NONE ? '' : v)}>
                          <SelectTrigger className="h-8"><SelectValue placeholder="—" /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value={NONE}>—</SelectItem>
                            <SelectItem value="I">I</SelectItem>
                            <SelectItem value="II">II</SelectItem>
                            <SelectItem value="III">III</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-xs">Severity</Label>
                        <Select value={form.watch('severity') || NONE} onValueChange={(v) => form.setValue('severity', v === NONE ? '' : v)}>
                          <SelectTrigger className="h-8"><SelectValue placeholder="—" /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value={NONE}>—</SelectItem>
                            <SelectItem value="NORMAL">Normal</SelectItem>
                            <SelectItem value="TIGHTENED">Tightened</SelectItem>
                            <SelectItem value="REDUCED">Reduced</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </>
                  )}
                </div>
                {/* Escalation — severity switching, driven by lot-acceptance history */}
                <div className="rounded-md border p-3 space-y-1">
                  <Label className="text-sm font-medium">Escalation (severity switching)</Label>
                  <p className="text-xs text-muted-foreground">
                    {form.watch('strategy') === 'Z14'
                      ? 'Severity tightens after rejected lots (Normal → Tightened) and relaxes after a sustained good run (→ Reduced), per Z1.4 switching rules. Starting severity is set in the plan above.'
                      : 'Inspection escalates to 100% after a rejected lot (C=0 convention).'}
                    {' '}Switching is automatic from lot-acceptance history (supplier scorecard) — engine wiring is a pending backend task.
                  </p>
                </div>
              </div>
              )}

              {watchedFamily === 'VARIABLES' && (
              <div className="space-y-3">
                <div>
                  <Label className="text-sm font-medium">Acceptance plan (variables · ANSI/ASQ Z1.9)</Label>
                  <p className="text-sm text-muted-foreground">
                    Measures one characteristic on the sample and accepts on the spread (x̄/s) vs the
                    acceptability constant k — resolved from lot size + AQL.
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs">Characteristic</Label>
                    <Select
                      value={(form.watch('variables_characteristic') as string | null) || NONE}
                      onValueChange={(v) => form.setValue('variables_characteristic', v === NONE ? null : v)}
                      disabled={readOnly || numericChars.length === 0}
                    >
                      <SelectTrigger className="h-8"><SelectValue placeholder="—" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value={NONE}>—</SelectItem>
                        {numericChars.map((c) => (
                          <SelectItem key={c.id} value={String(c.id)}>{c.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">AQL</Label>
                    <Select value={(form.watch('aql') as string | null) || NONE} onValueChange={(v) => form.setValue('aql', v === NONE ? null : v)}>
                      <SelectTrigger className="h-8"><SelectValue placeholder="—" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value={NONE}>—</SelectItem>
                        {AQL_SERIES.map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Inspection level</Label>
                    <Select value={form.watch('inspection_level') || NONE} onValueChange={(v) => form.setValue('inspection_level', v === NONE ? '' : v)}>
                      <SelectTrigger className="h-8"><SelectValue placeholder="II" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value={NONE}>—</SelectItem>
                        <SelectItem value="I">I</SelectItem>
                        <SelectItem value="II">II</SelectItem>
                        <SelectItem value="III">III</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                {numericChars.length === 0 && (
                  <p className="text-xs text-amber-600">
                    This step has no numeric measurements — add one (Measurements) before using variables sampling.
                  </p>
                )}
                <p className="text-xs text-muted-foreground">
                  Single vs double spec limit is taken from the characteristic's tolerances. The plan resolves
                  n + k at inspection time; the verdict shows the computed margin against k.
                </p>
                {/* Escalation — variables severity switching (Z1.9) */}
                <div className="rounded-md border p-3 space-y-1">
                  <Label className="text-sm font-medium">Escalation (severity switching)</Label>
                  <p className="text-xs text-muted-foreground">
                    Z1.9 severity tightens after rejected lots and relaxes after a sustained good run, from
                    lot-acceptance history (supplier scorecard) — engine wiring is a pending backend task.
                  </p>
                </div>
              </div>
              )}

              <Separator />

              {/* Quality gate */}
              <div className="space-y-3">
                <div>
                  <Label className="text-sm font-medium">Quality gate (automatic escalation)</Label>
                  <p className="text-sm text-muted-foreground">
                    Watch an aggregate signal on this step; fire actions when it crosses the threshold.
                    {watchedFamily === 'STREAMING'
                      ? ' (Tightening is configured by the escalation rules above.)'
                      : ' (Tightening is the severity switching above.)'}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs">Metric</Label>
                    <Select value={form.watch('gate_metric') || NONE} onValueChange={(v) => form.setValue('gate_metric', v === NONE ? '' : v)}>
                      <SelectTrigger className="h-8"><SelectValue placeholder="No gate" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value={NONE}>No gate</SelectItem>
                        <SelectItem value="CONSECUTIVE_FAILS">Consecutive failures</SelectItem>
                        <SelectItem value="FAIL_RATE_PCT">Failure rate (%)</SelectItem>
                        <SelectItem value="DEFECTIVE_COUNT">Defective count</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Threshold</Label>
                    <Input className="h-8" disabled={readOnly} placeholder="e.g. 2 or 50"
                      value={(form.watch('gate_threshold') as string | number | null) ?? ''}
                      onChange={(e) => form.setValue('gate_threshold', e.target.value === '' ? null : e.target.value)} />
                  </div>
                </div>

                {!!form.watch('gate_metric') && (
                  <div className="space-y-3 rounded-md border p-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <Label className="text-xs">Window</Label>
                        <Select value={form.watch('gate_window') || NONE} onValueChange={(v) => form.setValue('gate_window', v === NONE ? '' : v)}>
                          <SelectTrigger className="h-8"><SelectValue placeholder="—" /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value={NONE}>—</SelectItem>
                            <SelectItem value="WORK_ORDER">Whole work order at this step</SelectItem>
                            <SelectItem value="ROLLING_N">Rolling last N inspections</SelectItem>
                            <SelectItem value="LOT">Receiving lot sample</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      {form.watch('gate_window') === 'ROLLING_N' && (
                        <div className="space-y-1.5">
                          <Label className="text-xs">N (rolling window)</Label>
                          <Input className="h-8" type="number" min={1} disabled={readOnly}
                            value={form.watch('gate_window_n') ?? ''}
                            onChange={(e) => form.setValue('gate_window_n', e.target.value === '' ? null : Number(e.target.value))} />
                        </div>
                      )}
                      {form.watch('gate_metric') === 'FAIL_RATE_PCT' && (
                        <div className="space-y-1.5">
                          <Label className="text-xs">Min sample before firing</Label>
                          <Input className="h-8" type="number" min={1} disabled={readOnly}
                            value={form.watch('gate_min_sample') ?? ''}
                            onChange={(e) => form.setValue('gate_min_sample', e.target.value === '' ? null : Number(e.target.value))} />
                        </div>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label className="text-xs">Actions when tripped</Label>
                      {GATE_ACTIONS.map((a) => {
                        const selected = (form.watch('gate_actions') ?? []) as string[];
                        return (
                          <label key={a.value} className="flex items-center gap-2 text-sm">
                            <Checkbox checked={selected.includes(a.value)} disabled={readOnly}
                              onCheckedChange={() => form.setValue('gate_actions',
                                selected.includes(a.value) ? selected.filter((x) => x !== a.value) : [...selected, a.value])} />
                            {a.label}
                          </label>
                        );
                      })}
                    </div>

                    {((form.watch('gate_actions') ?? []) as string[]).includes('RAISE_CAPA_SCAR') && (
                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                          <Label className="text-xs">CAPA type</Label>
                          <Select value={form.watch('gate_capa_type') || 'CORRECTIVE'} onValueChange={(v) => form.setValue('gate_capa_type', v)}>
                            <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="CORRECTIVE">Corrective (CAPA)</SelectItem>
                              <SelectItem value="SUPPLIER">Supplier (SCAR)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-1.5">
                          <Label className="text-xs">Severity</Label>
                          <Select value={form.watch('gate_capa_severity') || 'MAJOR'} onValueChange={(v) => form.setValue('gate_capa_severity', v)}>
                            <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="CRITICAL">Critical</SelectItem>
                              <SelectItem value="MAJOR">Major</SelectItem>
                              <SelectItem value="MINOR">Minor</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    )}

                    {((form.watch('gate_actions') ?? []) as string[]).includes('REQUIRE_APPROVAL') && (
                      <div className="space-y-1.5">
                        <Label className="text-xs">Approval template</Label>
                        <Select value={form.watch('gate_approval_template') ?? NONE} onValueChange={(v) => form.setValue('gate_approval_template', v === NONE ? null : v)}>
                          <SelectTrigger className="h-8"><SelectValue placeholder="Select template…" /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value={NONE}>—</SelectItem>
                            {((approvalTemplates as { results?: any[] } | undefined)?.results ?? []).map((t: any) => (
                              <SelectItem key={t.id} value={String(t.id)}>{t.name ?? t.title ?? t.id}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}

                    <p className="text-xs text-muted-foreground">
                      Sending the subject somewhere — quarantine, scrap, rework, return-to-supplier — isn't
                      an action here; those are destination nodes reached by an edge. Set the step's decision
                      type to "Quality Gate (aggregate signal)" and draw the edge to that node; the firing
                      drives the routing.
                    </p>
                  </div>
                )}
              </div>

              {/* Validation Warnings */}
              {validationWarnings.length > 0 && (
                <div className="space-y-2">
                  {validationWarnings.map((warning, idx) => (
                    <Alert
                      key={idx}
                      variant={warning.type === 'error' ? 'destructive' : 'default'}
                      className={warning.type === 'warning' ? 'border-amber-500 bg-amber-50 dark:bg-amber-950/20' : ''}
                    >
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription className="text-sm">
                        {warning.message}
                      </AlertDescription>
                    </Alert>
                  ))}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                {readOnly ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => onOpenChange(false)}
                  >
                    Close
                  </Button>
                ) : (
                  <>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => onOpenChange(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      disabled={updateSamplingRules.isPending || hasErrors}
                    >
                      {updateSamplingRules.isPending ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        'Save Rules'
                      )}
                    </Button>
                  </>
                )}
              </div>
            </form>
          </FormProvider>
        )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
