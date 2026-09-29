import { useEffect, useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    useCreateStepTiming, useStepTiming, useUpdateStepTiming,
} from "@/hooks/useSchedulingSetup";
import type { components } from "@/lib/api/generated-types";
import { ATTENTION_LABEL, SetupFormFrame, StepSelect, parseMinutes, toastApiError } from "./shared";

type Attention = components["schemas"]["AttentionTypeEnum"];
const LIST = "/production/step-timings";

const MINUTE_FIELDS = [
    { key: "setup", label: "Setup", hint: "Internal setup: the machine is stopped while it happens." },
    { key: "cycle", label: "Cycle time per piece", hint: "Machine cycle for one piece. For CNC, from the program." },
    { key: "loadUnload", label: "Load / unload per piece", hint: "Operator touch time to load and unload one piece." },
    { key: "external", label: "External setup", hint: "Setup that can overlap the previous operation's run." },
] as const;
type MinuteKey = typeof MINUTE_FIELDS[number]["key"];

export function StepTimingFormPage() {
    const navigate = useNavigate();
    const params = useParams({ strict: false });
    const id = params.id as string | undefined;
    const mode = id ? "edit" : "create";

    const { data: existing, isLoading } = useStepTiming(id ?? "");
    const create = useCreateStepTiming();
    const update = useUpdateStepTiming();

    const [step, setStep] = useState("");
    const [attention, setAttention] = useState<Attention>("full");
    const [minutes, setMinutes] = useState<Record<MinuteKey, string>>({
        setup: "0", cycle: "0", loadUnload: "0", external: "0",
    });

    useEffect(() => {
        if (mode !== "edit" || !existing) return;
        setStep(String(existing.step));
        setAttention(existing.attention_type ?? "full");
        setMinutes({
            setup: String(existing.setup_minutes ?? 0),
            cycle: String(existing.cycle_time_minutes ?? 0),
            loadUnload: String(existing.load_unload_per_piece ?? 0),
            external: String(existing.external_setup_minutes ?? 0),
        });
    }, [mode, existing]);

    function submit() {
        if (!step) {
            toast.error("Pick the step these times describe");
            return;
        }
        const values: Partial<Record<MinuteKey, number>> = {};
        for (const f of MINUTE_FIELDS) {
            const n = parseMinutes(minutes[f.key], f.label);
            if (n === null) return;
            values[f.key] = n;
        }
        const payload = {
            step,
            attention_type: attention,
            setup_minutes: values.setup ?? 0,
            cycle_time_minutes: values.cycle ?? 0,
            load_unload_per_piece: values.loadUnload ?? 0,
            external_setup_minutes: values.external ?? 0,
        };
        const onSuccess = () => {
            toast.success(mode === "edit" ? "Step timing updated" : "Step timing created");
            navigate({ to: LIST });
        };
        const onError = (e: unknown) => toastApiError(e, ["step"]);
        if (mode === "edit" && id) update.mutate({ id, data: payload }, { onSuccess, onError });
        else create.mutate(payload, { onSuccess, onError });
    }

    return (
        <SetupFormFrame
            title={mode === "edit" ? "Edit step timing" : "New step timing"}
            description="A step's standard times. The scheduler and rough-cut capacity size every operation of this step from them."
            backTo={LIST}
            loading={mode === "edit" && isLoading}
            saving={create.isPending || update.isPending}
            submitLabel={mode === "edit" ? "Save changes" : "Create step timing"}
            onSubmit={submit}
        >
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Step</CardTitle>
                    <CardDescription>One timing per step. The step can't be changed once saved.</CardDescription>
                </CardHeader>
                <CardContent>
                    <StepSelect value={step} onChange={setStep} disabled={mode === "edit"} />
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Times (minutes)</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-4 sm:grid-cols-2">
                    {MINUTE_FIELDS.map((f) => (
                        <div key={f.key} className="space-y-1.5">
                            <Label htmlFor={`st-${f.key}`}>{f.label}</Label>
                            <Input
                                id={`st-${f.key}`} type="number" min={0} step="any" inputMode="decimal"
                                value={minutes[f.key]}
                                onChange={(e) => setMinutes((m) => ({ ...m, [f.key]: e.target.value }))}
                            />
                            <p className="text-xs text-muted-foreground">{f.hint}</p>
                        </div>
                    ))}
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Operator attention</CardTitle>
                    <CardDescription>
                        Whether the operator is tied to the machine for the whole cycle, or only
                        loads and unloads it.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Select value={attention} onValueChange={(v) => v && setAttention(v as Attention)}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                            {Object.entries(ATTENTION_LABEL).map(([value, label]) => (
                                <SelectItem key={value} value={value}>{label}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </CardContent>
            </Card>
        </SetupFormFrame>
    );
}
