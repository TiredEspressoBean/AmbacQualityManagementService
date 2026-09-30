import { RecordHistoryCard } from "@/components/data-management/RecordHistoryCard";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
    useCreateLifeLimitDefinition, useLifeLimitDefinition, useUpdateLifeLimitDefinition,
} from "@/hooks/useLifeLimitDefinitionsAdmin";
import { SetupFormFrame, toastApiError } from "@/pages/scheduling/setup/shared";

const LIST = "/editor/life-limit-definitions";

/** Blank → null; otherwise a non-negative number kept as the API's decimal string. */
function parseLimit(raw: string, label: string): string | null | undefined {
    const t = raw.trim();
    if (t === "") return null;
    const n = Number(t);
    if (!Number.isFinite(n) || n < 0) {
        toast.error(`${label} must be a number, 0 or more — or blank`);
        return undefined;
    }
    return t;
}

export function LifeLimitDefinitionFormPage() {
    const navigate = useNavigate();
    const params = useParams({ strict: false });
    const id = params.id as string | undefined;
    const mode = id ? "edit" : "create";

    const { data: existing, isLoading } = useLifeLimitDefinition(id ?? "");
    const create = useCreateLifeLimitDefinition();
    const update = useUpdateLifeLimitDefinition();

    const [name, setName] = useState("");
    const [unit, setUnit] = useState("");
    const [unitLabel, setUnitLabel] = useState("");
    const [calendar, setCalendar] = useState(false);
    const [soft, setSoft] = useState("");
    const [hard, setHard] = useState("");

    useEffect(() => {
        if (mode !== "edit" || !existing) return;
        setName(existing.name);
        setUnit(existing.unit);
        setUnitLabel(existing.unit_label);
        setCalendar(existing.is_calendar_based ?? false);
        setSoft(existing.soft_limit == null ? "" : String(Number(existing.soft_limit)));
        setHard(existing.hard_limit == null ? "" : String(Number(existing.hard_limit)));
    }, [mode, existing]);

    function submit() {
        if (!name.trim() || !unit.trim()) {
            toast.error("Give it a name and a unit");
            return;
        }
        const soft_limit = parseLimit(soft, "Soft limit");
        const hard_limit = parseLimit(hard, "Hard limit");
        if (soft_limit === undefined || hard_limit === undefined) return;
        const payload = {
            name: name.trim(), unit: unit.trim(), unit_label: unitLabel.trim() || unit.trim(),
            is_calendar_based: calendar, soft_limit, hard_limit,
        };
        const onSuccess = () => {
            toast.success(mode === "edit" ? "Definition saved" : "Definition created");
            navigate({ to: LIST });
        };
        const onError = (e: unknown) => toastApiError(e, ["name", "unit", "unit_label", "soft_limit", "hard_limit", "is_calendar_based"]);
        if (mode === "edit" && id) update.mutate({ id, data: payload }, { onSuccess, onError });
        else create.mutate(payload, { onSuccess, onError });
    }

    return (
        <SetupFormFrame
            title={mode === "edit" ? "Edit life limit" : "New life limit"}
            description="Something a part wears out by, and when it needs attention or must be retired."
            backTo={LIST}
            loading={mode === "edit" && isLoading}
            saving={create.isPending || update.isPending}
            submitLabel={mode === "edit" ? "Save changes" : "Create life limit"}
            onSubmit={submit}
            footer={mode === "edit" && id ? <RecordHistoryCard endpoint="LifeLimitDefinitions" id={id} model="lifelimitdefinition" /> : undefined}
        >
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">What it counts</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1.5 sm:col-span-2">
                        <Label htmlFor="lld-name">Name</Label>
                        <Input id="lld-name" value={name} onChange={(e) => setName(e.target.value)}
                            placeholder="Flight cycles, Shelf life…" />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="lld-unit">Unit</Label>
                        <Input id="lld-unit" value={unit} onChange={(e) => setUnit(e.target.value)}
                            placeholder="cycles, hours, days" />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="lld-label">Shown as</Label>
                        <Input id="lld-label" value={unitLabel} onChange={(e) => setUnitLabel(e.target.value)}
                            placeholder="Same as the unit" />
                    </div>
                    <div className="flex items-center justify-between rounded-md border p-3 sm:col-span-2">
                        <div>
                            <Label htmlFor="lld-cal">Counts calendar time</Label>
                            <p className="text-xs text-muted-foreground">
                                Ages from a reference date instead of being logged. The unit must then be
                                days, months or years.
                            </p>
                        </div>
                        <Switch id="lld-cal" checked={calendar} onCheckedChange={setCalendar} />
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Limits</CardTitle>
                    <CardDescription>Either may be blank.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1.5">
                        <Label htmlFor="lld-soft">Soft limit</Label>
                        <Input id="lld-soft" type="number" min={0} step="any" inputMode="decimal"
                            value={soft} onChange={(e) => setSoft(e.target.value)} />
                        <p className="text-xs text-muted-foreground">A warning, or when an overhaul is due.</p>
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="lld-hard">Hard limit</Label>
                        <Input id="lld-hard" type="number" min={0} step="any" inputMode="decimal"
                            value={hard} onChange={(e) => setHard(e.target.value)} />
                        <p className="text-xs text-muted-foreground">The part is blocked from use once it reaches this.</p>
                    </div>
                </CardContent>
            </Card>
        </SetupFormFrame>
    );
}
