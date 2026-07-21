/**
 * Start Work dialog — operator entry point into the DWI substep runtime.
 *
 * Opens from the WO Detail page header. The operator picks one or more
 * parts; we ensure a StepExecution exists for the first part's current
 * step, then route to the runtime with the remaining part ids carried in
 * a `?queue=` URL param. After "Complete step" on the runtime page, the
 * operator is auto-advanced to the next queued part.
 *
 * Why a queue (vs scanning each traveler between parts): shop-floor
 * reality. An operator at a station gets a tote of 5 parts and works
 * through them in serial — they shouldn't have to come back to a picker
 * after every one.
 *
 * Why on the WO Detail page (not a sidebar entry): operators arriving
 * via paper traveler already know the WO id. A first-class sidebar /
 * scanner entry is a separate design pass.
 */
import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Play, Loader2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { useRetrieveParts } from "@/hooks/parts";
import {
    useEnsureStepExecution,
    TrainingGateError,
    type TrainingGateInfo,
} from "@/hooks/useEnsureStepExecution";

type StartWorkDialogProps = {
    workOrderId: string;
};

export function StartWorkDialog({ workOrderId }: StartWorkDialogProps) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    // Insertion-ordered: the order an operator checks parts is the order
    // they're worked. Using an array (not a Set) preserves that order.
    const [selectedIds, setSelectedIds] = useState<string[]>([]);
    const [submitting, setSubmitting] = useState(false);

    const { data: partsData, isLoading } = useRetrieveParts(
        { work_order: workOrderId, limit: 500 },
        undefined,
        { enabled: open && !!workOrderId },
    );

    // Only parts routed to a step are workable. Group by step so an
    // operator at one station sees their station's parts together.
    const partsByStep = useMemo(() => {
        type PartRow = NonNullable<typeof partsData>["results"][number];
        type StepGroup = { stepName: string; parts: PartRow[] };
        const groups: Map<string, StepGroup> = new Map();
        for (const p of partsData?.results ?? []) {
            if (!p.step || !p.step_name) continue;
            const key = String(p.step);
            const existing = groups.get(key);
            if (existing) existing.parts.push(p);
            else groups.set(key, { stepName: p.step_name, parts: [p] });
        }
        return Array.from(groups.entries()).sort((a, b) =>
            a[1].stepName.localeCompare(b[1].stepName),
        );
    }, [partsData]);

    const allParts = useMemo(
        () => partsByStep.flatMap(([_id, g]) => g.parts),
        [partsByStep],
    );

    // The part list caps at 500 (§3.10). If the WO has more, the list is
    // incomplete — warn so the operator doesn't assume every part is shown.
    const partsTruncated =
        (partsData?.count ?? 0) > (partsData?.results?.length ?? 0);

    const togglePart = (partId: string) => {
        setSelectedIds((prev) =>
            prev.includes(partId)
                ? prev.filter((id) => id !== partId)
                : [...prev, partId],
        );
    };

    /** Toggle all parts in one step group at once. If every part is already
     *  selected, deselect them. Otherwise, add the missing ones in display
     *  order (so the queue ordering reflects the listed order). */
    const toggleAllInStep = (stepPartIds: string[]) => {
        setSelectedIds((prev) => {
            const allSelected = stepPartIds.every((id) => prev.includes(id));
            if (allSelected) {
                const toRemove = new Set(stepPartIds);
                return prev.filter((id) => !toRemove.has(id));
            }
            // Append missing ones in the order they appear in this group.
            const missing = stepPartIds.filter((id) => !prev.includes(id));
            return [...prev, ...missing];
        });
    };

    const ensureExec = useEnsureStepExecution();

    // Training gate (warn + supervisor override). When the backend blocks an
    // unqualified start, we hold the gate details here and open the override
    // panel instead of silently failing.
    const [gate, setGate] = useState<TrainingGateInfo | null>(null);
    const [overrideReason, setOverrideReason] = useState("");
    const [overriding, setOverriding] = useState(false);

    /** Ensure the first part's execution, then route into the runtime. Shared
     *  by the normal start and the supervisor-override retry. */
    const launch = async (opts?: { override?: boolean; overrideReason?: string }) => {
        const firstId = selectedIds[0];
        const first = allParts.find((p) => String(p.id) === firstId);
        if (!first) return;
        const stepId = String(first.step);

        // Only ensure the FIRST part's execution here. The remaining parts in
        // the queue get their executions ensured by the runtime page as the
        // operator advances — keeps this click cheap.
        const { executionId } = await ensureExec.mutateAsync({
            partId: firstId,
            stepId,
            override: opts?.override,
            overrideReason: opts?.overrideReason,
        });
        const queue = selectedIds.slice(1);

        // Reset + close before navigating so the dialog doesn't flash back
        // open if the operator hits the browser Back button.
        setSelectedIds([]);
        setOpen(false);
        setGate(null);
        setOverrideReason("");

        navigate({
            to: "/operator/steps/$stepId/substeps",
            params: { stepId },
            // The runtime route's search shape requires every key present
            // (fresh context — no inherited material_lot/osp_shipment/unit).
            search: {
                part: firstId,
                workOrder: workOrderId,
                execution: executionId,
                at: 0,
                queue: queue.length > 0 ? queue.join(",") : undefined,
                material_lot: undefined,
                osp_shipment: undefined,
                unit: undefined,
                debug: undefined,
            },
        });
    };

    const handleStart = async () => {
        if (selectedIds.length === 0) return;
        setSubmitting(true);
        try {
            await launch();
        } catch (e) {
            if (e instanceof TrainingGateError) {
                setGate(e.gate);
            } else {
                toast.error("Could not open the work surface", {
                    description: e instanceof Error ? e.message : undefined,
                });
            }
        } finally {
            setSubmitting(false);
        }
    };

    const handleOverride = async () => {
        if (!overrideReason.trim()) return;
        setOverriding(true);
        try {
            await launch({ override: true, overrideReason: overrideReason.trim() });
        } catch (e) {
            if (e instanceof TrainingGateError) {
                setGate(e.gate);
                toast.error(e.gate.detail);
            } else {
                toast.error("Override failed", {
                    description: e instanceof Error ? e.message : undefined,
                });
            }
        } finally {
            setOverriding(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={(v) => !submitting && setOpen(v)}>
            <DialogTrigger asChild>
                <Button className="gap-2">
                    <Play className="h-4 w-4" />
                    Start Work
                </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>Start work on parts</DialogTitle>
                    <DialogDescription>
                        Check the parts you'll work on, in the order you'll work them.
                        After you complete a part's step, the runtime moves to the next
                        checked part automatically.
                    </DialogDescription>
                </DialogHeader>

                {partsTruncated && (
                    <p className="rounded bg-destructive/10 px-3 py-2 text-xs text-destructive">
                        Showing the first {partsData?.results?.length ?? 0} of{" "}
                        {partsData?.count ?? 0} parts — the list is incomplete. Some
                        parts on this work order aren't shown here.
                    </p>
                )}

                <div className="max-h-[50vh] overflow-y-auto rounded-md border">
                    {isLoading ? (
                        <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Loading parts…
                        </div>
                    ) : partsByStep.length === 0 ? (
                        <p className="p-4 text-sm text-muted-foreground">
                            No parts on this WO are at a routed step.
                        </p>
                    ) : (
                        partsByStep.map(([stepId, { stepName, parts }]) => {
                            const stepPartIds = parts.map((p) => String(p.id));
                            const selectedInStep = stepPartIds.filter((id) =>
                                selectedIds.includes(id),
                            );
                            const allSelected =
                                stepPartIds.length > 0 &&
                                selectedInStep.length === stepPartIds.length;
                            const someSelected =
                                selectedInStep.length > 0 && !allSelected;
                            return (
                            <div key={stepId} className="border-b last:border-b-0">
                                <label className="bg-muted/40 px-3 py-1.5 text-xs font-medium text-muted-foreground sticky top-0 flex items-center gap-2 cursor-pointer hover:bg-muted/60">
                                    <Checkbox
                                        checked={allSelected ? true : someSelected ? "indeterminate" : false}
                                        onCheckedChange={() => toggleAllInStep(stepPartIds)}
                                        aria-label={`Select all in ${stepName}`}
                                    />
                                    <span>{stepName}</span>
                                    <span className="text-[10px] opacity-60">
                                        ({selectedInStep.length} / {parts.length})
                                    </span>
                                </label>
                                {parts.map((p) => {
                                    const id = String(p.id);
                                    const orderIdx = selectedIds.indexOf(id);
                                    const checked = orderIdx !== -1;
                                    return (
                                        <label
                                            key={id}
                                            className="flex items-center gap-3 px-3 py-2 text-sm cursor-pointer hover:bg-muted/30"
                                        >
                                            <Checkbox
                                                checked={checked}
                                                onCheckedChange={() => togglePart(id)}
                                            />
                                            <span className="font-medium">{p.ERP_id}</span>
                                            <span className="text-xs text-muted-foreground">
                                                {p.part_status?.replace(/_/g, " ").toLowerCase()}
                                            </span>
                                            {checked && (
                                                <Badge variant="secondary" className="ml-auto text-[10px]">
                                                    #{orderIdx + 1}
                                                </Badge>
                                            )}
                                        </label>
                                    );
                                })}
                            </div>
                            );
                        })
                    )}
                </div>

                <DialogFooter className="sm:items-center">
                    {selectedIds.length > 0 && (
                        <span className="mr-auto text-xs text-muted-foreground">
                            {selectedIds.length} selected · will work in checked order
                        </span>
                    )}
                    <Button
                        variant="outline"
                        onClick={() => setOpen(false)}
                        disabled={submitting}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleStart}
                        disabled={selectedIds.length === 0 || submitting}
                    >
                        {submitting ? (
                            <>
                                <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                                Opening…
                            </>
                        ) : selectedIds.length > 1 ? (
                            `Start (${selectedIds.length} parts)`
                        ) : (
                            "Start"
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>

            {/* Training gate — block on missing competency, supervisor override */}
            <Dialog
                open={!!gate}
                onOpenChange={(v) => {
                    if (overriding) return;
                    if (!v) {
                        setGate(null);
                        setOverrideReason("");
                    }
                }}
            >
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <ShieldAlert className="h-5 w-5 text-destructive" />
                            Not qualified for this step
                        </DialogTitle>
                        <DialogDescription>
                            {gate?.can_override
                                ? "The operator isn't qualified. As a supervisor you can override with a logged reason."
                                : "You aren't qualified to start this step. A supervisor must override to proceed."}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3">
                        <p className="text-xs font-medium text-destructive mb-1.5">
                            Missing training
                        </p>
                        <ul className="space-y-1 text-sm">
                            {gate?.missing.map((m, i) => (
                                <li key={i} className="flex justify-between gap-3">
                                    <span className="font-medium">{m.training}</span>
                                    <span className="text-xs text-muted-foreground">
                                        {m.reason}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {gate?.can_override && (
                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground">
                                Override reason (required — recorded on the execution)
                            </label>
                            <Textarea
                                value={overrideReason}
                                onChange={(e) => setOverrideReason(e.target.value)}
                                placeholder="e.g. line-down, trainee working under direct supervision"
                                rows={3}
                            />
                        </div>
                    )}

                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => {
                                setGate(null);
                                setOverrideReason("");
                            }}
                            disabled={overriding}
                        >
                            Cancel
                        </Button>
                        {gate?.can_override && (
                            <Button
                                variant="destructive"
                                onClick={handleOverride}
                                disabled={!overrideReason.trim() || overriding}
                            >
                                {overriding ? (
                                    <>
                                        <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                                        Overriding…
                                    </>
                                ) : (
                                    "Override & start"
                                )}
                            </Button>
                        )}
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Dialog>
    );
}
