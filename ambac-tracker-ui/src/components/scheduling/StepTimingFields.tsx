/**
 * A step's standard times, edited on the step's own form: what the scheduler and
 * rough-cut capacity size each operation from. One timing per step; saving creates
 * it the first time and updates it after.
 *
 * Setup and cycle also show what the step records measure and which the scheduler
 * uses; "Use measured" copies the measurement into the field, to save like any edit.
 */
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { MeasuredLine, SourceBadge, measuredValue, type Aspect } from "@/components/scheduling/MeasuredTiming";
import {
    useCreateStepTiming, useMeasuredStepTimings, useStepTimings, useUpdateStepTiming,
} from "@/hooks/useSchedulingSetup";
import type { components } from "@/lib/api/generated-types";
import { ATTENTION_LABEL, parseMinutes, toastApiError, useAllows } from "@/pages/scheduling/setup/shared";

type Attention = components["schemas"]["AttentionTypeEnum"];

const FIELDS = [
    { key: "setup_minutes", label: "Setup", hint: "Machine stopped while it happens." },
    { key: "cycle_time_minutes", label: "Cycle, per piece", hint: "One piece through the machine." },
    { key: "load_unload_per_piece", label: "Load / unload, per piece", hint: "Operator touch time." },
    { key: "external_setup_minutes", label: "External setup", hint: "Can overlap the previous run." },
] as const;
type Key = typeof FIELDS[number]["key"];

/** The fields a measurement exists for. */
const MEASURED: Partial<Record<Key, Aspect>> = { setup_minutes: "setup", cycle_time_minutes: "cycle" };

export function StepTimingFields({ stepId }: { stepId: string }) {
    const allows = useAllows();
    const { data, isLoading } = useStepTimings({ step: stepId, limit: 1 });
    const existing = data?.results?.[0];
    const { data: measuredRows } = useMeasuredStepTimings(stepId);
    const measured = measuredRows?.[0];
    const canSave = existing ? allows("change_steptiming") : allows("add_steptiming");
    const create = useCreateStepTiming();
    const update = useUpdateStepTiming();

    const [attention, setAttention] = useState<Attention>("full");
    const [values, setValues] = useState<Record<Key, string>>({
        setup_minutes: "0", cycle_time_minutes: "0", load_unload_per_piece: "0", external_setup_minutes: "0",
    });

    useEffect(() => {
        if (!existing) return;
        setAttention(existing.attention_type ?? "full");
        setValues({
            setup_minutes: String(existing.setup_minutes ?? 0),
            cycle_time_minutes: String(existing.cycle_time_minutes ?? 0),
            load_unload_per_piece: String(existing.load_unload_per_piece ?? 0),
            external_setup_minutes: String(existing.external_setup_minutes ?? 0),
        });
    }, [existing]);

    function save() {
        const parsed: Partial<Record<Key, number>> = {};
        for (const f of FIELDS) {
            const n = parseMinutes(values[f.key], f.label);
            if (n === null) return;
            parsed[f.key] = n;
        }
        const payload = { step: stepId, attention_type: attention, ...parsed };
        const onSuccess = () => toast.success("Timing saved");
        const onError = (e: unknown) => toastApiError(e, ["step"]);
        if (existing) update.mutate({ id: existing.id, data: payload }, { onSuccess, onError });
        else create.mutate(payload, { onSuccess, onError });
    }

    if (isLoading) return <p className="text-sm text-muted-foreground">Loading…</p>;

    return (
        <div className="space-y-4">
            {!existing && (
                <p className="text-sm text-muted-foreground">
                    No timing yet. Until it has one, the scheduler can't size this step.
                </p>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
                {FIELDS.map((f) => (
                    <div key={f.key} className="space-y-1.5">
                        <Label htmlFor={`stf-${f.key}`}>{f.label} (min)</Label>
                        <Input id={`stf-${f.key}`} type="number" min={0} step="any" inputMode="decimal"
                            value={values[f.key]} disabled={!canSave}
                            onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))} />
                        <p className="text-xs text-muted-foreground">{f.hint}</p>
                        {MEASURED[f.key] && (() => {
                            const aspect = MEASURED[f.key]!;
                            const value = measuredValue(measured, aspect);
                            return (
                                <div className="flex flex-wrap items-center gap-2">
                                    <SourceBadge source={aspect === "setup" ? measured?.setup_in_use : measured?.cycle_in_use} />
                                    <MeasuredLine m={measured} aspect={aspect} />
                                    {canSave && value != null && String(value) !== values[f.key] && (
                                        <Button type="button" variant="link" size="sm" className="h-auto p-0 text-xs"
                                            onClick={() => setValues((v) => ({ ...v, [f.key]: String(value) }))}>
                                            Use measured
                                        </Button>
                                    )}
                                </div>
                            );
                        })()}
                    </div>
                ))}
                <div className="space-y-1.5">
                    <Label>Operator attention</Label>
                    <Select value={attention} onValueChange={(v) => v && setAttention(v as Attention)}
                        {...(!canSave ? { disabled: true } : {})}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                            {Object.entries(ATTENTION_LABEL).map(([value, label]) => (
                                <SelectItem key={value} value={value}>{label}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </div>
            {canSave && (
                <Button size="sm" onClick={save} disabled={create.isPending || update.isPending}>
                    {create.isPending || update.isPending ? "Saving…" : existing ? "Save timing" : "Add timing"}
                </Button>
            )}
        </div>
    );
}
