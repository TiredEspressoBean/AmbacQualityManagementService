import { useMemo, useState } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { ArrowLeft, AlertTriangle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
    Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from "@/components/ui/tooltip";

import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Pencil, Undo2 } from "lucide-react";

import { useRebuildPlan } from "@/hooks/useRebuildPlan";
import { useRetrieveCore } from "@/hooks/useRetrieveCore";
import {
    useCreateSlotOverride, useDeleteSlotOverride, useUpdateSlotOverride,
} from "@/hooks/useRebuildSlotOverrides";
import { apiErrorBody, apiErrorField } from "@/lib/api/describeApiError";
import type { Schema } from "@/lib/api/types";

type PlanSlot = Schema<"RebuildPlan">["slots"][number];
type Resolution = Schema<"RebuildSlotOverrideRequest">["resolution"];

// Resolution vocabulary, in one place. The first is the unremarkable outcome — the
// part came out serviceable and goes back — and everything else costs money or time.
const RESOLUTION_LABEL: Record<string, string> = {
    REUSE: "Reuse as-is",
    RECONDITION: "Recondition",
    REPLACE_POOL: "Replace — recovered stock",
    REPLACE_BUY: "Replace — buy",
};

function resolutionVariant(resolution: string): "default" | "secondary" | "outline" | "destructive" {
    switch (resolution) {
        case "REUSE":
            return "secondary";
        case "RECONDITION":
            return "outline";
        case "REPLACE_BUY":
            return "destructive";
        default:
            return "default";
    }
}

const SOURCE_LABEL: Record<string, string> = {
    HARVESTED_THIS_CORE: "from this unit",
    HARVESTED_POOL: "recovered stock",
    PURCHASED: "purchase",
};

export function RebuildPlanPage() {
    const { id } = useParams({ from: "/reman/cores/$id/rebuild" });
    const { data: core } = useRetrieveCore(id);
    const { data: plan, isLoading, isError, error } = useRebuildPlan(id, { enabled: !!id });

    // The screen opens on the decisions. Twenty-eight slots resolved "reuse as-is"
    // are not what anyone came here to read.
    const [showSettled, setShowSettled] = useState(false);

    // Curation state. An overridden slot always shows, even when the planner chose
    // REUSE — a decision someone made is exactly the row worth seeing.
    const [editing, setEditing] = useState<PlanSlot | null>(null);
    const [draftResolution, setDraftResolution] = useState<Resolution>("REUSE");
    const [draftReason, setDraftReason] = useState("");

    const createOverride = useCreateSlotOverride();
    const updateOverride = useUpdateSlotOverride();
    const deleteOverride = useDeleteSlotOverride();
    const savingOverride = createOverride.isPending || updateOverride.isPending;

    function openEditor(slot: PlanSlot) {
        setEditing(slot);
        setDraftResolution((slot.resolution as Resolution) ?? "REUSE");
        setDraftReason(slot.is_overridden ? slot.reason : "");
    }

    function onOverrideError(err: unknown) {
        const body = apiErrorBody(err);
        toast.error(
            apiErrorField(body, "reason") ??
            apiErrorField(body, "detail") ??
            apiErrorField(body, "non_field_errors") ??
            (err as Error)?.message ??
            "unknown error",
        );
    }

    function saveOverride() {
        if (!editing) return;
        if (!draftReason.trim()) {
            toast.error("Say why — an override with no reason cannot be told from a misclick later");
            return;
        }
        const done = () => {
            toast.success("Decision recorded");
            setEditing(null);
        };
        if (editing.is_overridden && editing.override_id) {
            updateOverride.mutate(
                { id: editing.override_id, data: { resolution: draftResolution, reason: draftReason } },
                { onSuccess: done, onError: onOverrideError },
            );
        } else {
            createOverride.mutate(
                {
                    core: id,
                    bom_line: editing.bom_line_id ?? "",
                    position: editing.position ?? "",
                    resolution: draftResolution,
                    reason: draftReason,
                },
                { onSuccess: done, onError: onOverrideError },
            );
        }
    }

    function revert(slot: PlanSlot) {
        if (!slot.override_id) return;
        deleteOverride.mutate(slot.override_id, {
            onSuccess: () => toast.success("Back to the proposed resolution"),
            onError: onOverrideError,
        });
    }

    const slots = useMemo(() => plan?.slots ?? [], [plan]);
    // Overridden rows count as worth showing whatever they resolved to: someone made
    // a call, and hiding it under "settled" would bury the most interesting rows.
    const needing = useMemo(
        () => slots.filter((s) => s.needs_decision || s.is_overridden), [slots]);
    const settled = useMemo(
        () => slots.filter((s) => !s.needs_decision && !s.is_overridden), [slots]);
    const visible = showSettled ? slots : needing;

    if (isLoading) {
        return (
            <div className="max-w-5xl mx-auto py-10">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 w-64 rounded bg-muted" />
                    <div className="h-64 rounded bg-muted" />
                </div>
            </div>
        );
    }

    if (isError || !plan) {
        return (
            <div className="max-w-5xl mx-auto py-10 space-y-4">
                <Button variant="ghost" size="sm" asChild>
                    <Link to="/reman/cores/$id" params={{ id }}>
                        <ArrowLeft className="mr-1 h-4 w-4" />
                        Back to core
                    </Link>
                </Button>
                <p className="text-destructive">
                    Could not build a rebuild plan: {(error as Error)?.message ?? "unknown error"}
                </p>
            </div>
        );
    }

    return (
        <TooltipProvider>
            <div className="max-w-5xl mx-auto py-10 space-y-6">
                <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                        <Button variant="ghost" size="icon" asChild>
                            <Link to="/reman/cores/$id" params={{ id }}>
                                <ArrowLeft className="h-4 w-4" />
                            </Link>
                        </Button>
                        <div>
                            <h1 className="text-2xl font-bold flex items-center gap-2">
                                Rebuild plan — {plan.core_number}
                                {plan.fulfilment_mode === "REPAIR_RETURN" && (
                                    <Badge variant="outline">Returns to customer</Badge>
                                )}
                            </h1>
                            <p className="text-muted-foreground">
                                {core?.core_type_name ?? "Core"}
                                {plan.bom_revision ? ` · assembly BOM rev ${plan.bom_revision}` : ""}
                                {plan.entry_scope ? ` · ${plan.entry_scope}` : ""}
                            </p>
                        </div>
                    </div>
                </div>

                {/* A proposal is not a commitment, and the screen should not imply it is. */}
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base">Proposed, not committed</CardTitle>
                        <CardDescription>
                            Nothing here is reserved or ordered. This is what the system would
                            put back into this unit, and why — read it before anyone commits
                            capacity or money to it.
                        </CardDescription>
                    </CardHeader>
                    {plan.warnings.length > 0 && (
                        <CardContent className="pt-0">
                            <ul className="space-y-2">
                                {plan.warnings.map((w, i) => (
                                    <li key={i} className="flex gap-2 text-sm text-muted-foreground">
                                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                                        <span>{w}</span>
                                    </li>
                                ))}
                            </ul>
                        </CardContent>
                    )}
                </Card>

                {/* Operations before slots: what we will DO to the unit is the bigger
                    commitment, and a slot resolution is what put each one here. */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex flex-wrap items-baseline gap-3">
                            <span>Operations</span>
                            <span className="text-sm font-normal text-muted-foreground tabular-nums">
                                {plan.operations.length}
                            </span>
                        </CardTitle>
                        <CardDescription>
                            The work this rebuild needs. Each one is here because the entry
                            scope includes it or a finding raised it — nothing is on the job
                            without a reason you can challenge.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {plan.operations.length === 0 ? (
                            <p className="py-6 text-center text-muted-foreground">
                                No operations resolved — no rebuild level or repair codes are
                                configured for this core type.
                            </p>
                        ) : (
                            <div className="w-full overflow-x-auto rounded-md border">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Operation</TableHead>
                                            <TableHead>Code</TableHead>
                                            <TableHead>Because</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {plan.operations.map((op) => (
                                            <TableRow key={op.step_id}>
                                                <TableCell className="font-medium">
                                                    {op.step_name}
                                                </TableCell>
                                                <TableCell>
                                                    <Badge variant="secondary" title={op.code_name}>
                                                        {op.code}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell className="text-sm text-muted-foreground">
                                                    {op.because.join("; ")}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex flex-wrap items-baseline gap-3">
                            <span>Slots</span>
                            <span className="text-sm font-normal text-muted-foreground tabular-nums">
                                {needing.length} need a decision · {settled.length} settled
                            </span>
                        </CardTitle>
                        <CardDescription>
                            One row per position on the unit. A slot is filled by a specific
                            component, not a quantity — a grade B nozzle from this unit is not
                            interchangeable with any other.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {slots.length === 0 ? (
                            <p className="py-8 text-center text-muted-foreground">
                                No slots — there is no released assembly BOM for this core type.
                            </p>
                        ) : (
                            <>
                                <div className="w-full overflow-x-auto rounded-md border">
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>Position</TableHead>
                                                <TableHead>Needs</TableHead>
                                                <TableHead>Found at teardown</TableHead>
                                                <TableHead>Proposed</TableHead>
                                                <TableHead>Why</TableHead>
                                                <TableHead>Decide</TableHead>
                                                <TableHead>Options</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {visible.map((slot, i) => (
                                                <TableRow key={`${slot.component_type_id}-${slot.position}-${i}`}>
                                                    <TableCell className="font-mono text-sm">
                                                        {slot.position || "—"}
                                                    </TableCell>
                                                    <TableCell>{slot.component_type_name}</TableCell>
                                                    <TableCell className="text-sm text-muted-foreground">
                                                        {slot.finding}
                                                    </TableCell>
                                                    <TableCell>
                                                        <div className="flex flex-col gap-1">
                                                            <Badge variant={resolutionVariant(slot.resolution)}>
                                                                {RESOLUTION_LABEL[slot.resolution] ?? slot.resolution}
                                                            </Badge>
                                                            {slot.is_overridden && (
                                                                <span className="text-xs text-muted-foreground">
                                                                    overridden &mdash; proposed{" "}
                                                                    {RESOLUTION_LABEL[slot.proposed_resolution] ??
                                                                        slot.proposed_resolution}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </TableCell>
                                                    <TableCell className="text-sm text-muted-foreground">
                                                        {slot.reason}
                                                    </TableCell>
                                                    <TableCell className="whitespace-nowrap">
                                                        <Button
                                                            size="icon" variant="ghost"
                                                            onClick={() => openEditor(slot)}
                                                            aria-label={`Change ${slot.component_type_name}`}
                                                            disabled={!slot.bom_line_id}
                                                        >
                                                            <Pencil className="h-4 w-4" />
                                                        </Button>
                                                        {slot.is_overridden && (
                                                            <Button
                                                                size="icon" variant="ghost"
                                                                onClick={() => revert(slot)}
                                                                disabled={deleteOverride.isPending}
                                                                aria-label="Back to proposed"
                                                            >
                                                                <Undo2 className="h-4 w-4" />
                                                            </Button>
                                                        )}
                                                    </TableCell>
                                                    <TableCell>
                                                        {slot.candidates.length === 0 ? (
                                                            <span className="text-sm text-muted-foreground">
                                                                none
                                                            </span>
                                                        ) : (
                                                            <Tooltip>
                                                                <TooltipTrigger asChild>
                                                                    <span className="cursor-default text-sm underline decoration-dotted underline-offset-4">
                                                                        {slot.candidates.length} available
                                                                    </span>
                                                                </TooltipTrigger>
                                                                <TooltipContent className="max-w-sm">
                                                                    <ul className="space-y-1 text-xs">
                                                                        {slot.candidates.map((c) => (
                                                                            <li key={c.id}>
                                                                                <span className="font-mono">{c.label}</span>
                                                                                {" — "}
                                                                                {SOURCE_LABEL[c.kind] ?? c.kind}
                                                                                {c.grade ? `, grade ${c.grade}` : ""}
                                                                                {c.detail ? ` (${c.detail})` : ""}
                                                                            </li>
                                                                        ))}
                                                                    </ul>
                                                                </TooltipContent>
                                                            </Tooltip>
                                                        )}
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </div>
                                {settled.length > 0 && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setShowSettled((v) => !v)}
                                    >
                                        {showSettled
                                            ? `Hide ${settled.length} settled`
                                            : `Show ${settled.length} settled`}
                                    </Button>
                                )}
                            </>
                        )}
                    </CardContent>
                </Card>
            </div>

            <Dialog open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            {editing?.component_type_name}
                            {editing?.position ? ` · ${editing.position}` : ""}
                        </DialogTitle>
                        <DialogDescription>
                            Teardown found: {editing?.finding}. The system proposed{" "}
                            {RESOLUTION_LABEL[
                                (editing?.is_overridden
                                    ? editing?.proposed_resolution
                                    : editing?.resolution) ?? ""
                            ] ?? "—"}.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="space-y-1.5">
                            <Label>Resolution</Label>
                            <Select
                                value={draftResolution}
                                onValueChange={(v) => v && setDraftResolution(v as Resolution)}
                            >
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {Object.entries(RESOLUTION_LABEL).map(([value, label]) => (
                                        <SelectItem key={value} value={value}>{label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="override-reason">Why</Label>
                            <Textarea
                                id="override-reason" rows={3} value={draftReason}
                                onChange={(e) => setDraftReason(e.target.value)}
                                placeholder="What the proposal missed"
                            />
                            <p className="text-xs text-muted-foreground">
                                Required. This is the row that answers why the unit was built
                                this way when somebody asks in six months.
                            </p>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
                        <Button onClick={saveOverride} disabled={savingOverride}>
                            {savingOverride ? "Saving…" : "Record decision"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </TooltipProvider>
    );
}
