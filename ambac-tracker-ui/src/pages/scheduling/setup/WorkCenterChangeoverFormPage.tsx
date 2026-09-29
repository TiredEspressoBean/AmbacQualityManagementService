import { useEffect, useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    useChangeover, useCreateChangeover, useUpdateChangeover,
} from "@/hooks/useSchedulingSetup";
import {
    EquipmentSelect, SetupFormFrame, StepSelect, parseMinutes, toastApiError,
} from "./shared";

const LIST = "/production/work-center-changeovers";

export function WorkCenterChangeoverFormPage() {
    const navigate = useNavigate();
    const params = useParams({ strict: false });
    const id = params.id as string | undefined;
    const mode = id ? "edit" : "create";

    const { data: existing, isLoading } = useChangeover(id ?? "");
    const create = useCreateChangeover();
    const update = useUpdateChangeover();

    const [equipment, setEquipment] = useState("");
    const [fromStep, setFromStep] = useState("");
    const [toStep, setToStep] = useState("");
    const [minutes, setMinutes] = useState("0");

    useEffect(() => {
        if (mode !== "edit" || !existing) return;
        setEquipment(String(existing.equipment));
        setFromStep(String(existing.from_step));
        setToStep(String(existing.to_step));
        setMinutes(String(existing.changeover_minutes ?? 0));
    }, [mode, existing]);

    function submit() {
        if (!equipment || !fromStep || !toStep) {
            toast.error("Pick the machine and both steps");
            return;
        }
        const n = parseMinutes(minutes, "Changeover");
        if (n === null) return;
        const payload = { equipment, from_step: fromStep, to_step: toStep, changeover_minutes: n };
        const onSuccess = () => {
            toast.success(mode === "edit" ? "Changeover updated" : "Changeover created");
            navigate({ to: LIST });
        };
        const onError = (e: unknown) => toastApiError(e, ["equipment", "from_step", "to_step", "changeover_minutes"]);
        if (mode === "edit" && id) update.mutate({ id, data: payload }, { onSuccess, onError });
        else create.mutate(payload, { onSuccess, onError });
    }

    return (
        <SetupFormFrame
            title={mode === "edit" ? "Edit changeover" : "New changeover"}
            description="Minutes to reconfigure a machine when it switches from running one step to another."
            backTo={LIST}
            loading={mode === "edit" && isLoading}
            saving={create.isPending || update.isPending}
            submitLabel={mode === "edit" ? "Save changes" : "Create changeover"}
            onSubmit={submit}
        >
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Machine</CardTitle>
                </CardHeader>
                <CardContent>
                    <EquipmentSelect value={equipment} onChange={setEquipment} />
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">The switch</CardTitle>
                    <CardDescription>
                        One row per machine, from step and to step. Switching back the other way
                        is its own row.
                    </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1.5">
                        <Label>From step</Label>
                        <StepSelect value={fromStep} onChange={setFromStep} placeholder="Step it was running" />
                    </div>
                    <div className="space-y-1.5">
                        <Label>To step</Label>
                        <StepSelect value={toStep} onChange={setToStep} placeholder="Step it switches to" />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="co-min">Changeover (minutes)</Label>
                        <Input
                            id="co-min" type="number" min={0} step="any" inputMode="decimal"
                            value={minutes} onChange={(e) => setMinutes(e.target.value)}
                        />
                    </div>
                </CardContent>
            </Card>
        </SetupFormFrame>
    );
}
