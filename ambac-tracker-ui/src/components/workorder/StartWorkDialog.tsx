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
import { Input } from "@/components/ui/input";
import { useRetrieveParts } from "@/hooks/parts";
import {
    useEnsureStepExecution,
    TrainingGateError,
    type TrainingGateInfo,
    type OverrideCredentials,
} from "@/hooks/useEnsureStepExecution";
import { useWorkAuthorization, type WorkAuthRow } from "@/hooks/useWorkAuthorization";

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

    // Pre-flight: which of these parts is the current user qualified to work?
    // Authorization is per-step, so every part in a step group shares a verdict.
    const partIds = useMemo(() => allParts.map((p) => String(p.id)), [allParts]);
    const { data: authData } = useWorkAuthorization(partIds, open);
    const authByPart = useMemo(() => {
        const m = new Map<string, WorkAuthRow>();
        // The schema types `missing` as a loose dict; normalize to {training,reason}.
        for (const r of authData?.results ?? []) {
            m.set(String(r.part), {
                part: String(r.part),
                step: r.step ? String(r.step) : null,
                authorized: !!r.authorized,
                missing: (r.missing ?? []).map((x) => ({
                    training: String((x as Record<string, unknown>).training ?? ""),
                    reason: String((x as Record<string, unknown>).reason ?? ""),
                })),
            });
        }
        return m;
    }, [authData]);

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

    // Training gate. When the backend blocks an unqualified start, we hold the
    // details here and open the supervisor re-authorization panel — a DIFFERENT
    // supervisor must sign in to authorize (never the operator themselves).
    const [gate, setGate] = useState<TrainingGateInfo | null>(null);
    const [supEmail, setSupEmail] = useState("");
    const [supPassword, setSupPassword] = useState("");
    const [overrideReason, setOverrideReason] = useState("");
    const [overriding, setOverriding] = useState(false);

    const resetOverride = () => {
        setGate(null);
        setSupEmail("");
        setSupPassword("");
        setOverrideReason("");
    };

    /** Ensure the first part's execution, then route into the runtime. Shared
     *  by the normal start and the supervisor-override retry. */
    const launch = async (opts?: { override?: OverrideCredentials }) => {
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
        });
        const queue = selectedIds.slice(1);

        // Reset + close before navigating so the dialog doesn't flash back
        // open if the operator hits the browser Back button.
        setSelectedIds([]);
        setOpen(false);
        resetOverride();

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
        // Pre-flight the first part (the one we launch). If the operator isn't
        // qualified, open the gate panel straight away — no doomed create — so
        // the resume path (existing execution) is gated too, not just create.
        const firstAuth = authByPart.get(selectedIds[0]);
        if (firstAuth && !firstAuth.authorized) {
            setGate({
                code: "training_not_authorized",
                detail: "You are not qualified for this step.",
                missing: firstAuth.missing,
            });
            return;
        }
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

    const overrideReady =
        supEmail.trim() !== "" && supPassword !== "" && overrideReason.trim() !== "";

    const handleOverride = async () => {
        if (!overrideReady) return;
        setOverriding(true);
        try {
            await launch({
                override: {
                    email: supEmail.trim(),
                    password: supPassword,
                    reason: overrideReason.trim(),
                },
            });
        } catch (e) {
            if (e instanceof TrainingGateError) {
                // Keep the panel open with the specific reason (bad password,
                // not a supervisor, same person, throttled…).
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
                            // Authorization is per-step → all parts in this group
                            // share one verdict; read it off the first part.
                            const groupAuth = authByPart.get(stepPartIds[0]);
                            const stepBlocked = groupAuth ? !groupAuth.authorized : false;
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
                                    {stepBlocked && (
                                        <Badge
                                            variant="outline"
                                            className="ml-auto gap-1 border-amber-500/50 text-amber-600 dark:text-amber-400"
                                        >
                                            <ShieldAlert className="h-3 w-3" />
                                            Training needed
                                        </Badge>
                                    )}
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

            {/* Training gate — block on missing competency; a DIFFERENT
                supervisor re-authenticates to authorize (second-person). */}
            <Dialog
                open={!!gate}
                onOpenChange={(v) => {
                    if (overriding) return;
                    if (!v) resetOverride();
                }}
            >
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <ShieldAlert className="h-5 w-5 text-destructive" />
                            {gate?.code === "assigned_to_other"
                                ? "Assigned to someone else"
                                : "Not qualified for this step"}
                        </DialogTitle>
                        <DialogDescription>
                            {gate?.code === "assigned_to_other"
                                ? "This step is assigned to another operator. A supervisor must sign in below to reassign it — logged against their name."
                                : "The operator isn't qualified. A supervisor must sign in below to authorize this work — logged against their name."}
                        </DialogDescription>
                    </DialogHeader>

                    {gate?.missing && gate.missing.length > 0 && (
                        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3">
                            <p className="text-xs font-medium text-destructive mb-1.5">
                                Missing training
                            </p>
                            <ul className="space-y-1 text-sm">
                                {gate.missing.map((m, i) => (
                                    <li key={i} className="flex justify-between gap-3">
                                        <span className="font-medium">{m.training}</span>
                                        <span className="text-xs text-muted-foreground">
                                            {m.reason}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {gate?.code === "assigned_to_other" && gate.assigned_to_name && (
                        <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-sm">
                            Currently assigned to{" "}
                            <span className="font-medium">{gate.assigned_to_name}</span>.
                        </div>
                    )}

                    <div className="space-y-2">
                        <p className="text-xs font-medium text-muted-foreground">
                            Supervisor authorization
                        </p>
                        <Input
                            type="email"
                            autoComplete="off"
                            value={supEmail}
                            onChange={(e) => setSupEmail(e.target.value)}
                            placeholder="Supervisor email"
                        />
                        <Input
                            type="password"
                            autoComplete="off"
                            value={supPassword}
                            onChange={(e) => setSupPassword(e.target.value)}
                            placeholder="Supervisor password"
                        />
                        <Textarea
                            value={overrideReason}
                            onChange={(e) => setOverrideReason(e.target.value)}
                            placeholder={
                                gate?.code === "assigned_to_other"
                                    ? "Reason for reassignment (required)"
                                    : "Reason (required — e.g. line-down, trainee under direct supervision)"
                            }
                            rows={2}
                        />
                    </div>

                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={resetOverride}
                            disabled={overriding}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleOverride}
                            disabled={!overrideReady || overriding}
                        >
                            {overriding ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                                    Authorizing…
                                </>
                            ) : (
                                "Authorize & start"
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Dialog>
    );
}
