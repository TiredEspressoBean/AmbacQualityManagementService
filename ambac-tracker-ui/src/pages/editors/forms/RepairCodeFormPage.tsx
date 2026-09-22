import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

import {
    useCreateRepairCode, useRetrieveRepairCode, useUpdateRepairCode,
} from "@/hooks/useRepairCodes";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { useRetrieveSteps } from "@/hooks/useRetrieveSteps";
import { apiErrorBody, apiErrorField } from "@/lib/api/describeApiError";
import type { Schema } from "@/lib/api/types";

// Mirrors the generated enum rather than restating it as loose strings, so a new
// trigger on the model is a type error here instead of a silent mismatch.
type Trigger = NonNullable<Schema<"RepairCodeRequest">["trigger"]>;

const TRIGGERS: { value: Trigger; label: string }[] = [
    { value: "RECONDITION", label: "Component needs work before it goes back" },
    { value: "REPLACE_POOL", label: "Slot is filled from recovered stock" },
    { value: "REPLACE_BUY", label: "Slot is filled by a purchase" },
    { value: "REUSE", label: "Component goes back as-is" },
    { value: "ALWAYS", label: "Always — base scope, whatever the finding" },
    { value: "PRESET", label: "Only when a rebuild level includes it" },
];

// "Any component" needs a sentinel: neither null nor "" can be a SelectItem value.
const ANY_COMPONENT = "__any__";

export function RepairCodeFormPage() {
    const navigate = useNavigate();
    const params = useParams({ strict: false });
    const id = params.id as string | undefined;
    const mode = id ? "edit" : "create";

    const { data: existing, isLoading } = useRetrieveRepairCode(id ?? "", { enabled: !!id });
    const { data: partTypesData } = useRetrievePartTypes({ limit: 200 });
    const { data: stepsData } = useRetrieveSteps({ limit: 500 });

    const [code, setCode] = useState("");
    const [name, setName] = useState("");
    const [trigger, setTrigger] = useState<Trigger>("RECONDITION");
    const [componentType, setComponentType] = useState<string>(ANY_COMPONENT);
    const [stepIds, setStepIds] = useState<Set<string>>(new Set());
    const [notes, setNotes] = useState("");

    useEffect(() => {
        if (mode !== "edit" || !existing) return;
        setCode(existing.code ?? "");
        setName(existing.name ?? "");
        setTrigger((existing.trigger as Trigger) ?? "RECONDITION");
        setComponentType(existing.component_type ? String(existing.component_type) : ANY_COMPONENT);
        setStepIds(new Set((existing.steps ?? []).map(String)));
        setNotes(existing.notes ?? "");
    }, [mode, existing]);

    const partTypes = useMemo(() => partTypesData?.results ?? [], [partTypesData]);
    const steps = useMemo(() => stepsData?.results ?? [], [stepsData]);

    const create = useCreateRepairCode();
    const update = useUpdateRepairCode();
    const saving = create.isPending || update.isPending;

    function toggleStep(stepId: string) {
        setStepIds((prev) => {
            const next = new Set(prev);
            if (next.has(stepId)) next.delete(stepId);
            else next.add(stepId);
            return next;
        });
    }

    function submit() {
        if (!code.trim() || !name.trim()) {
            toast.error("A code and a name are required");
            return;
        }
        const payload = {
            code: code.trim(),
            name: name.trim(),
            trigger,
            component_type: componentType === ANY_COMPONENT ? null : componentType,
            steps: Array.from(stepIds),
            notes,
        };
        const onSuccess = () => {
            toast.success(mode === "edit" ? "Repair code updated" : "Repair code created");
            navigate({ to: "/editor/repair-codes" });
        };
        const onError = (err: unknown) => {
            const body = apiErrorBody(err);
            const message =
                apiErrorField(body, "code") ??
                apiErrorField(body, "detail") ??
                apiErrorField(body, "non_field_errors") ??
                (err as Error)?.message ??
                "unknown error";
            toast.error(message);
        };

        if (mode === "edit" && id) {
            update.mutate({ id, data: payload }, { onSuccess, onError });
        } else {
            create.mutate(payload, { onSuccess, onError });
        }
    }

    if (mode === "edit" && isLoading) {
        return (
            <div className="max-w-3xl mx-auto py-10">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 w-64 rounded bg-muted" />
                    <div className="h-64 rounded bg-muted" />
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto py-10 space-y-6">
            <div className="flex items-center gap-3">
                <Button variant="ghost" size="icon" onClick={() => navigate({ to: "/editor/repair-codes" })}>
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                    <h1 className="text-2xl font-bold">
                        {mode === "edit" ? "Edit repair code" : "New repair code"}
                    </h1>
                    <p className="text-muted-foreground">
                        What a finding adds to a rebuild. Codes compose — a unit with two
                        findings gets the union of both codes' operations.
                    </p>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Identity</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid gap-4 sm:grid-cols-2">
                        <div className="space-y-1.5">
                            <Label htmlFor="code">Code</Label>
                            <Input
                                id="code" value={code} onChange={(e) => setCode(e.target.value)}
                                placeholder="NZL-RECON" className="font-mono"
                            />
                            <p className="text-xs text-muted-foreground">
                                The short identifier the shop uses.
                            </p>
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="name">Name</Label>
                            <Input
                                id="name" value={name} onChange={(e) => setName(e.target.value)}
                                placeholder="Recondition injector nozzle"
                            />
                            <p className="text-xs text-muted-foreground">
                                In the words the bench would use.
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">When it is raised</CardTitle>
                    <CardDescription>
                        A code is raised by a finding on a slot, or it is base scope. Which one
                        decides whether a planner ever sees it as a choice.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-1.5">
                        <Label>Raised by</Label>
                        <Select
                            value={trigger}
                            onValueChange={(v) => v && setTrigger(v as Trigger)}
                        >
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {TRIGGERS.map((t) => (
                                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-1.5">
                        <Label>Component</Label>
                        <Select
                            value={componentType}
                            onValueChange={(v) => v && setComponentType(v)}
                        >
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value={ANY_COMPONENT}>
                                    Any component — whole-unit work
                                </SelectItem>
                                {partTypes.map((pt) => (
                                    <SelectItem key={pt.id} value={String(pt.id)}>
                                        {pt.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <p className="text-xs text-muted-foreground">
                            Leave as "any" for work that is not about one component — a final
                            test raised by any slot taking this resolution.
                        </p>
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">
                        Operations it adds{" "}
                        <span className="text-sm font-normal text-muted-foreground tabular-nums">
                            {stepIds.size} selected
                        </span>
                    </CardTitle>
                    <CardDescription>
                        A code with no operations adds no work — it would be raised and change
                        nothing.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="max-h-72 space-y-2 overflow-y-auto rounded-md border p-3">
                        {steps.length === 0 ? (
                            <p className="py-4 text-center text-sm text-muted-foreground">
                                No steps found.
                            </p>
                        ) : (
                            steps.map((step) => {
                                const sid = String(step.id);
                                return (
                                    <label
                                        key={sid}
                                        className="flex cursor-pointer items-center gap-2 text-sm"
                                    >
                                        <Checkbox
                                            checked={stepIds.has(sid)}
                                            onCheckedChange={() => toggleStep(sid)}
                                        />
                                        <span>{step.name}</span>
                                        {step.part_type_name && (
                                            <span className="text-muted-foreground">
                                                · {step.part_type_name}
                                            </span>
                                        )}
                                    </label>
                                );
                            })
                        )}
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Notes</CardTitle>
                </CardHeader>
                <CardContent>
                    <Textarea
                        value={notes} onChange={(e) => setNotes(e.target.value)}
                        placeholder="Anything the bench should know about this code"
                        rows={3}
                    />
                </CardContent>
            </Card>

            <div className="flex gap-3">
                <Button onClick={submit} disabled={saving} className="flex-1">
                    {saving ? "Saving…" : mode === "edit" ? "Save changes" : "Create repair code"}
                </Button>
                <Button
                    variant="ghost"
                    onClick={() => navigate({ to: "/editor/repair-codes" })}
                    disabled={saving}
                >
                    Cancel
                </Button>
            </div>
        </div>
    );
}
