import { RecordHistoryCard } from "@/components/data-management/RecordHistoryCard";
import { RecordArchiveCard } from "@/components/data-management/RecordArchiveCard";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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

    const [code, setCode] = useState("");
    const [name, setName] = useState("");
    const [trigger, setTrigger] = useState<Trigger>("RECONDITION");
    const [componentType, setComponentType] = useState<string>(ANY_COMPONENT);
    const [notes, setNotes] = useState("");
    // Required (the safe default): declining it returns the unit unrepaired.
    const [required, setRequired] = useState(true);

    useEffect(() => {
        if (mode !== "edit" || !existing) return;
        setCode(existing.code ?? "");
        setName(existing.name ?? "");
        setTrigger((existing.trigger as Trigger) ?? "RECONDITION");
        setComponentType(existing.component_type ? String(existing.component_type) : ANY_COMPONENT);
        setNotes(existing.notes ?? "");
        setRequired(existing.required ?? true);
    }, [mode, existing]);

    const partTypes = useMemo(() => partTypesData?.results ?? [], [partTypesData]);

    const create = useCreateRepairCode();
    const update = useUpdateRepairCode();
    const saving = create.isPending || update.isPending;


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
            notes,
            required,
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
                        A repair a finding can call for. When a unit's findings raise this
                        code, the check that offers it sends the unit down its Repair step.
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

            {/* Where this repair happens: the Repair nodes carrying this code, drawn off a
                check in the process editor. Since 2026-10-12 a code doesn't add steps to a
                route — every step runs, and a check sends the unit to its Repair node when
                the code is raised. (The older per-code step list is kept as stored, unused.) */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Where it's done</CardTitle>
                    <CardDescription>
                        Add a Repair step carrying this code off the check that finds the need,
                        in the process editor. A unit goes there when this code is raised for it.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {(existing?.repair_step_names ?? []).length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                            No Repair step carries this code yet, so raising it sends a unit
                            nowhere — a finding that raises it has no planned repair.
                        </p>
                    ) : (
                        <ul className="flex flex-wrap gap-1.5">
                            {(existing?.repair_step_names ?? []).map((n) => (
                                <li key={n}><Badge variant="secondary">{n}</Badge></li>
                            ))}
                        </ul>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">When the customer declines it</CardTitle>
                    <CardDescription>
                        A customer asked to authorise this repair on their own unit can decline
                        it. Your call, for each repair: can the unit still be rebuilt without it?
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <label className="flex items-start gap-2 text-sm">
                        <Checkbox
                            checked={required}
                            onCheckedChange={(v) => setRequired(v === true)}
                            aria-label="Required for the rebuild"
                            className="mt-0.5"
                        />
                        <span>
                            <span className="font-medium">Required for the rebuild</span>
                            <span className="block text-muted-foreground">
                                {required
                                    ? "Declining it returns the unit unrepaired."
                                    : "Optional: if declined, the unit is rebuilt without it and its paperwork says so."}
                            </span>
                        </span>
                    </label>
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
            {mode === "edit" && id && (
                <div className="max-w-3xl mx-auto py-6">
                    <div className="space-y-6"><RecordHistoryCard endpoint="RepairCodes" id={id} model="repaircode" /><RecordArchiveCard endpoint="RepairCodes" id={id} model="repaircode" /></div>
                </div>
            )}
        </div>
    );
}
