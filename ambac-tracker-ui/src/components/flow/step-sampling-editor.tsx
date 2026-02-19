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
import { Target, Loader2, ArrowRight, TrendingUp, AlertTriangle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useRetrieveStepWithSamplingRules } from '@/hooks/useRetrieveStepWithSamplingRules';
import { useUpdateStepSamplingRules } from '@/hooks/useUpdateStepSamplingRules';
import SamplingRulesEditor from '@/components/SamplingRulesEditor';
import { toast } from 'sonner';

const samplingRuleSchema = z.object({
  rule_type: z.string().min(1),
  value: z.union([z.string(), z.number(), z.null()]),
  order: z.number().min(0),
});

const formSchema = z.object({
  rules: z.array(samplingRuleSchema),
  fallback_rules: z.array(samplingRuleSchema).optional(),
  fallback_threshold: z.number().nullable().optional(),
  fallback_duration: z.number().nullable().optional(),
});

type FormValues = z.infer<typeof formSchema>;

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

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      rules: [],
      fallback_rules: [],
      fallback_threshold: null,
      fallback_duration: null,
    },
  });

  // Populate form when step data loads
  // Note: active_ruleset and fallback_ruleset come from extended step type via hook
  useEffect(() => {
    if (step && open) {
      const stepWithRules = step as any;
      form.reset({
        rules: stepWithRules.active_ruleset?.rules ?? [],
        fallback_rules: stepWithRules.fallback_ruleset?.rules ?? [],
        fallback_threshold: stepWithRules.active_ruleset?.fallback_threshold ?? null,
        fallback_duration: stepWithRules.active_ruleset?.fallback_duration ?? null,
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

  const handleSubmit = (values: FormValues) => {
    const normalizedRules = normalizeRules(values.rules);
    const normalizedFallbackRules = normalizeRules(values.fallback_rules ?? []);

    updateSamplingRules.mutate(
      {
        id: stepId,
        data: {
          rules: normalizedRules as any,
          fallback_rules: normalizedFallbackRules as any,
          fallback_threshold: values.fallback_threshold ?? undefined,
          fallback_duration: values.fallback_duration ?? undefined,
        },
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

  const watchedRules = form.watch('rules') ?? [];
  const watchedFallbackRules = form.watch('fallback_rules') ?? [];
  const watchedThreshold = form.watch('fallback_threshold');
  const watchedDuration = form.watch('fallback_duration');
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

  const hasErrors = validationWarnings.some(w => w.type === 'error');

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] p-0 gap-0">
        <DialogHeader className="p-6 pb-0">
          <DialogTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Sampling Rules for "{stepName}"
          </DialogTitle>
          <DialogDescription>
            Configure when quality sampling occurs at this step
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
                <SamplingRulesEditor name="rules" label="Primary Rules" />
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
                <SamplingRulesEditor name="fallback_rules" label="Escalation Rules" />

                {/* Trigger settings - only show when there are escalation rules */}
                {hasFallbackRules && (
                  <div className="flex items-center gap-6 p-4 rounded-lg border bg-muted/30">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="fallback_threshold" className="text-sm whitespace-nowrap">
                        Escalate after
                      </Label>
                      <Input
                        id="fallback_threshold"
                        type="number"
                        min={1}
                        className="w-16 h-8"
                        value={watchedThreshold ?? ''}
                        onChange={(e) => {
                          const parsed = parseInt(e.target.value);
                          form.setValue('fallback_threshold', isNaN(parsed) ? null : parsed);
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
