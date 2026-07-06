import { useState } from "react";
import { useParams, useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Ruler, Target, FileText, Settings, ListChecks, ArrowRight, Loader2 } from "lucide-react";
import { MeasurementsEditor } from "@/components/flow/measurements-editor";
import { StepSamplingEditor } from "@/components/flow/step-sampling-editor";
import { StepDocumentsEditor } from "@/components/flow/step-documents-editor";
import { useRetrieveStepWithSamplingRules } from "@/hooks/useRetrieveStepWithSamplingRules";
import { useRetrieveMeasurementDefinitions } from "@/hooks/useRetrieveMeasurementDefinitions";
import { useSubsteps, useCreateSubstep } from "@/hooks/useSubsteps";
import { SAMPLE_QUALITY_STATUS, SAMPLE_INSPECTION_SIGNATURES } from "@/lib/dwi/samples";
import { withFreshNodeId, newNodeId } from "@/lib/dwi/node-id";

/** A measurement characteristic as returned by the MeasurementDefinitions list. */
type CharacteristicDef = {
  id: string | number;
  label?: string;
  type?: string;
  unit?: string | null;
  nominal?: string | number | null;
  upper_tol?: string | number | null;
  lower_tol?: string | number | null;
  characteristic_number?: string | null;
};

const num = (v: string | number | null | undefined): number | null =>
  v == null || v === "" ? null : Number(v);

/**
 * Build a starter inspection-substep body wired to the plan's characteristics:
 * one `measurementInput` per characteristic (linked to its MeasurementDefinition
 * so the reading records a MeasurementResult), an overall disposition status, and
 * an inspector sign-off. Running this DWI records the results to the lot's
 * QualityReport (the substep is created as an inspection point).
 */
function buildReceivingInspectionBody(characteristics: CharacteristicDef[]): object {
  const measurementNodes = characteristics.map((c) => ({
    type: "measurementInput",
    attrs: {
      node_id: newNodeId(),
      label: c.label ?? "Measurement",
      unit: c.unit ?? "",
      nominal: num(c.nominal),
      upper_tol: num(c.upper_tol),
      lower_tol: num(c.lower_tol),
      required: true,
      characteristic_number: c.characteristic_number ?? "",
      measurement_definition_id: String(c.id),
      measurement_type: c.type === "PASS_FAIL" ? "PASS_FAIL" : "NUMERIC",
    },
  }));
  return {
    type: "doc",
    content: [
      {
        type: "paragraph",
        content: [{
          type: "text",
          text: "Inspect the sampled units against the receiving criteria. Record each measurement, then set the overall lot disposition and sign off.",
        }],
      },
      ...measurementNodes,
      withFreshNodeId(SAMPLE_QUALITY_STATUS),
      withFreshNodeId(SAMPLE_INSPECTION_SIGNATURES),
    ],
  };
}

/** Human label for the configured sampling method, derived from the active ruleset. */
function samplingMethodLabel(ar: { strategy?: string; aql?: unknown; rules?: { rule_type?: string }[] } | undefined): string {
  if (!ar) return "Not configured";
  if (ar.strategy === "Z19" || (ar.rules ?? []).some((r) => r.rule_type === "VARIABLES")) return "Variables (Z1.9)";
  const isLot = !!(ar.strategy || ar.aql ||
    (ar.rules ?? []).some((r) => r.rule_type === "AQL" || r.rule_type === "C_ZERO"));
  if (isLot) return ar.strategy === "Z14" ? "Lot acceptance — Z1.4" : "Lot acceptance — C=0";
  if ((ar.rules ?? []).length) return "Per-part streaming";
  return "Not configured";
}

/**
 * Receiving Inspection Plan editor — a standalone (process-free) RECEIVING step.
 * Reuses the exact same configuration dialogs as the flow editor's step panel
 * (measurements, sampling method incl. variables, documents), keyed to this step.
 */
export function ReceivingInspectionPlanEditorPage() {
  const { stepId } = useParams({ strict: false }) as { stepId: string };
  const navigate = useNavigate();

  const { data: step } = useRetrieveStepWithSamplingRules({ params: { id: stepId } });
  // eslint-disable-next-line local/no-as-any -- active_ruleset is populated by the extended endpoint, not in the base type
  const activeRuleset = (step as any)?.active_ruleset;
  const stepName = (step as { name?: string } | undefined)?.name ?? "Receiving plan";

  const { data: measurements } = useRetrieveMeasurementDefinitions({ step: stepId }, undefined, { enabled: !!stepId });
  const measurementCount = measurements?.count ?? 0;

  // DWI substeps — same authoring surface as in-process steps. The operator
  // runtime launches these from the receiving inspection page when present.
  const { data: substepsResponse } = useSubsteps(stepId ? { step: stepId } : undefined);
  const substepCount = substepsResponse?.count ?? 0;
  const createSubstep = useCreateSubstep();

  const goToSubsteps = () =>
    navigate({ to: "/production/receiving-plans/$stepId/substeps", params: { stepId } });

  // Author: when the plan has no substeps yet, seed a starter inspection
  // substep pre-wired to the plan's characteristics (so the operator records
  // results to a QualityReport out of the box), then open the editor. Once
  // substeps exist, just open the editor.
  const handleAuthor = async () => {
    if (substepCount > 0) { goToSubsteps(); return; }
    try {
      await createSubstep.mutateAsync({
        step: stepId,
        order: 0,
        title: "Incoming inspection",
        is_inspection_point: true,
        body_blocks: buildReceivingInspectionBody(
          (measurements?.results ?? []) as CharacteristicDef[],
        ),
      } as never);
    } catch {
      toast.error("Could not create the inspection substep");
      return;
    }
    goToSubsteps();
  };

  const [measurementsOpen, setMeasurementsOpen] = useState(false);
  const [samplingOpen, setSamplingOpen] = useState(false);
  const [documentsOpen, setDocumentsOpen] = useState(false);

  return (
    <div className="max-w-3xl mx-auto p-4 space-y-4">
      <Button variant="ghost" size="sm" onClick={() => navigate({ to: "/production/receiving-plans" })}>
        <ArrowLeft className="h-4 w-4 mr-1" /> Receiving Inspection Plans
      </Button>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {stepName}
            <Badge variant="outline">Purchased · process-free</Badge>
          </CardTitle>
          <CardDescription>
            What to inspect and how to sample when this part type is received from a supplier.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Characteristics */}
          <div className="flex items-center justify-between border-b pb-3">
            <div className="flex items-center gap-2 text-sm">
              <Ruler className="h-4 w-4 text-muted-foreground" />
              <span>Characteristics</span>
              {measurementCount > 0 && <Badge variant="secondary" className="text-xs">{measurementCount}</Badge>}
            </div>
            <Button variant="outline" size="sm" onClick={() => setMeasurementsOpen(true)}>
              <Settings className="h-4 w-4 mr-1" /> Configure
            </Button>
          </div>

          {/* Sampling method */}
          <div className="flex items-center justify-between border-b pb-3">
            <div className="flex items-center gap-2 text-sm">
              <Target className="h-4 w-4 text-muted-foreground" />
              <span>Sampling method</span>
              <Badge variant="secondary" className="text-xs">{samplingMethodLabel(activeRuleset)}</Badge>
            </div>
            <Button variant="outline" size="sm" onClick={() => setSamplingOpen(true)}>
              <Settings className="h-4 w-4 mr-1" /> Configure
            </Button>
          </div>

          {/* Work instructions (DWI substeps) */}
          <div className="flex items-center justify-between border-b pb-3">
            <div className="flex items-center gap-2 text-sm">
              <ListChecks className="h-4 w-4 text-muted-foreground" />
              <span>Work instructions (DWI)</span>
              {substepCount > 0 && <Badge variant="secondary" className="text-xs">{substepCount}</Badge>}
            </div>
            <Button variant="outline" size="sm" onClick={handleAuthor} disabled={createSubstep.isPending}>
              {createSubstep.isPending
                ? <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                : substepCount > 0 ? <Settings className="h-4 w-4 mr-1" /> : <ArrowRight className="h-4 w-4 mr-1" />}
              {substepCount > 0 ? "Edit" : "Author"}
            </Button>
          </div>

          {/* Documents */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span>Documents</span>
            </div>
            <Button variant="outline" size="sm" onClick={() => setDocumentsOpen(true)}>
              <Settings className="h-4 w-4 mr-1" /> Configure
            </Button>
          </div>
        </CardContent>
      </Card>

      <MeasurementsEditor stepId={stepId} stepName={stepName} open={measurementsOpen} onOpenChange={setMeasurementsOpen} />
      <StepSamplingEditor stepId={stepId} stepName={stepName} open={samplingOpen} onOpenChange={setSamplingOpen} />
      <StepDocumentsEditor stepId={stepId} stepName={stepName} open={documentsOpen} onOpenChange={setDocumentsOpen} />
    </div>
  );
}
