import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Trash2 } from "lucide-react";

import { useTrainingRequirements } from "@/hooks/useTrainingRequirements";
import { useTrainingTypes } from "@/hooks/useTrainingTypes";
import { useCreateTrainingRequirement } from "@/hooks/useCreateTrainingRequirement";
import { useDeleteTrainingRequirement } from "@/hooks/useDeleteTrainingRequirement";

/**
 * Reusable "required training" editor for any TrainingRequirement scope
 * (job role, step, process, or equipment type). Lists the scope's existing
 * requirements and lets you add/remove (training type + min level). Each
 * change persists immediately via the requirement create/delete endpoints —
 * the scope target (step/job_role/…) must already be a saved id.
 */

export type RequirementScope =
    | { job_role: string }
    | { step: string }
    | { process: string }
    | { equipment_type: string };

const LEVELS = [
    { value: "1", label: "L1 — Trainee" },
    { value: "2", label: "L2 — Assisted" },
    { value: "3", label: "L3 — Qualified" },
    { value: "4", label: "L4 — Expert" },
];

export function TrainingRequirementsEditor({
    scope,
    title = "Required competencies",
    description = "The training this must hold, at what level. Personnel are measured against this in the training matrix / authorization gate.",
    readOnly = false,
}: {
    scope: RequirementScope;
    title?: string;
    description?: string;
    readOnly?: boolean;
}) {
    const { data: reqData, isLoading } = useTrainingRequirements({ queries: scope as never }, { retry: false });
    const requirements = reqData?.results ?? [];
    const { data: typesData } = useTrainingTypes({});
    const trainingTypes = typesData?.results ?? [];
    const createReq = useCreateTrainingRequirement();
    const deleteReq = useDeleteTrainingRequirement();

    const [typeId, setTypeId] = useState("");
    const [level, setLevel] = useState("3");

    const usedTypeIds = new Set(requirements.map((r) => r.training_type));
    const available = trainingTypes.filter((t) => !usedTypeIds.has(t.id));

    const add = () => {
        if (!typeId) return;
        createReq.mutate(
            { training_type: typeId, ...scope, min_level: Number(level) } as never,
            {
                onSuccess: () => { toast.success("Requirement added."); setTypeId(""); setLevel("3"); },
                onError: () => toast.error("Failed to add requirement."),
            },
        );
    };

    const remove = (id: string) => {
        deleteReq.mutate({ id }, {
            onSuccess: () => toast.success("Requirement removed."),
            onError: () => toast.error("Failed to remove requirement."),
        });
    };

    return (
        <div className="space-y-3 rounded-md border p-4">
            <div>
                <h2 className="text-sm font-semibold">{title}</h2>
                <p className="text-xs text-muted-foreground">{description}</p>
            </div>

            {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
            ) : requirements.length === 0 ? (
                <p className="text-sm text-muted-foreground">No required competencies yet.</p>
            ) : (
                <ul className="divide-y rounded-md border">
                    {requirements.map((r) => {
                        const info = r.training_type_info as { name?: string } | null | undefined;
                        return (
                            <li key={r.id} className="flex items-center justify-between gap-2 p-2 text-sm">
                                <span className="font-medium">{info?.name ?? "—"}</span>
                                <div className="flex items-center gap-2">
                                    <Badge variant="outline" title={r.min_level_display ?? undefined}>
                                        needs L{r.min_level}
                                    </Badge>
                                    {!readOnly && (
                                        <Button type="button" variant="ghost" size="icon" className="text-destructive" onClick={() => remove(r.id)} title="Remove">
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    )}
                                </div>
                            </li>
                        );
                    })}
                </ul>
            )}

            {!readOnly && (
                <div className="flex flex-wrap items-end gap-2">
                    <div className="min-w-[200px] flex-1">
                        <label className="mb-1 block text-xs text-muted-foreground">Training type</label>
                        <Select value={typeId} onValueChange={setTypeId}>
                            <SelectTrigger><SelectValue placeholder="Select a training type" /></SelectTrigger>
                            <SelectContent>
                                {available.length === 0 && <div className="p-2 text-xs text-muted-foreground">All types already added.</div>}
                                {available.map((t) => (
                                    <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="w-[140px]">
                        <label className="mb-1 block text-xs text-muted-foreground">Min level</label>
                        <Select value={level} onValueChange={setLevel}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {LEVELS.map((l) => (<SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>))}
                            </SelectContent>
                        </Select>
                    </div>
                    <Button type="button" onClick={add} disabled={!typeId || createReq.isPending}>Add</Button>
                </div>
            )}
        </div>
    );
}
