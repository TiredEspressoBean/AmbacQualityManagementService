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
    useCreateStepAffinity, useStepAffinity, useUpdateStepAffinity,
} from "@/hooks/useSchedulingSetup";
import type { components } from "@/lib/api/generated-types";
import {
    AFFINITY_LABEL, EquipmentSelect, SetupFormFrame, StepSelect, toastApiError,
} from "./shared";

type Affinity = components["schemas"]["AffinityEnum"];
const LIST = "/production/step-equipment-affinities";

export function StepEquipmentAffinityFormPage() {
    const navigate = useNavigate();
    const params = useParams({ strict: false });
    const id = params.id as string | undefined;
    const mode = id ? "edit" : "create";

    const { data: existing, isLoading } = useStepAffinity(id ?? "");
    const create = useCreateStepAffinity();
    const update = useUpdateStepAffinity();

    const [step, setStep] = useState("");
    const [equipment, setEquipment] = useState("");
    const [affinity, setAffinity] = useState<Affinity>("eligible");
    const [override, setOverride] = useState("");

    useEffect(() => {
        if (mode !== "edit" || !existing) return;
        setStep(String(existing.step));
        setEquipment(String(existing.equipment));
        setAffinity(existing.affinity ?? "eligible");
        setOverride(existing.cycle_time_override == null ? "" : String(existing.cycle_time_override));
    }, [mode, existing]);

    function submit() {
        if (!step || !equipment) {
            toast.error("Pick both the step and the machine");
            return;
        }
        let cycle: number | null = null;
        if (override.trim() !== "") {
            cycle = Number(override);
            if (!Number.isFinite(cycle) || cycle < 0) {
                toast.error("Cycle override must be a number of minutes, 0 or more — or blank");
                return;
            }
        }
        const payload = { step, equipment, affinity, cycle_time_override: cycle };
        const onSuccess = () => {
            toast.success(mode === "edit" ? "Eligibility updated" : "Eligibility created");
            navigate({ to: LIST });
        };
        const onError = (e: unknown) => toastApiError(e, ["step", "equipment", "cycle_time_override"]);
        if (mode === "edit" && id) update.mutate({ id, data: payload }, { onSuccess, onError });
        else create.mutate(payload, { onSuccess, onError });
    }

    return (
        <SetupFormFrame
            title={mode === "edit" ? "Edit machine eligibility" : "New machine eligibility"}
            description="A machine that can run a step, and how well. The scheduler only places a step on machines listed for it."
            backTo={LIST}
            loading={mode === "edit" && isLoading}
            saving={create.isPending || update.isPending}
            submitLabel={mode === "edit" ? "Save changes" : "Create eligibility"}
            onSubmit={submit}
        >
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Step and machine</CardTitle>
                    <CardDescription>One row per step and machine pair.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1.5">
                        <Label>Step</Label>
                        <StepSelect value={step} onChange={setStep} />
                    </div>
                    <div className="space-y-1.5">
                        <Label>Machine</Label>
                        <EquipmentSelect value={equipment} onChange={setEquipment} />
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">How well it runs the step</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1.5">
                        <Label>Affinity</Label>
                        <Select value={affinity} onValueChange={(v) => v && setAffinity(v as Affinity)}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {Object.entries(AFFINITY_LABEL).map(([value, label]) => (
                                    <SelectItem key={value} value={value}>{label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <p className="text-xs text-muted-foreground">
                            The scheduler favours preferred and dialed-in machines when it has a choice.
                        </p>
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="aff-cycle">Cycle time override (minutes)</Label>
                        <Input
                            id="aff-cycle" type="number" min={0} step="any" inputMode="decimal"
                            value={override} onChange={(e) => setOverride(e.target.value)}
                            placeholder="Blank = the step's standard cycle"
                        />
                        <p className="text-xs text-muted-foreground">
                            Per-piece cycle on this machine, for a machine faster or slower than the standard.
                        </p>
                    </div>
                </CardContent>
            </Card>
        </SetupFormFrame>
    );
}
