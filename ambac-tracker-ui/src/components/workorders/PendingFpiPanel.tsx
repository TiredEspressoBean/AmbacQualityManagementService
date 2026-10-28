/**
 * QA's pending first-piece inspections for one work order.
 *
 * The QA home page's "Start check" button navigates to
 * `/workorder/$id/control` — but until now nothing FPI-shaped rendered there,
 * so the most obvious route into a buy-off dead-ended. This is that
 * destination.
 *
 * It complements the runtime hold rather than duplicating it: the runtime is
 * where the *operator* meets the hold and can fetch QA to co-sign at the
 * station; this is where *QA* works their own queue for a WO, without needing
 * an operator's work session at all. That split is the whole point — an FPI is
 * keyed on (work_order, step), so it was never really part-session-shaped.
 *
 * Sits beside `PendingDecisionsPanel`, which is the same idea for PENDING
 * sampling decisions.
 */
import { useState } from "react";
import { Loader2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

import { api } from "@/lib/api/generated";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FpiSignOffDialog, type FpiVerdict } from "@/components/fpi-sign-off-dialog";
import { useFpiGetOrCreate, useFpiRecords } from "@/hooks/useFpiRecords";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { useAcknowledgeFpi } from "@/hooks/useAcknowledgeFpi";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { useReportActivity } from "@/hooks/useReportActivity";

// The `*_info` fields are declared shapes now rather than DictField, so the
// row type comes from the client instead of being guessed at here.
type FpiRow = Awaited<ReturnType<typeof api.api_FPIRecords_list>>["results"][number];

export function PendingFpiPanel({ workOrderId, onActivity }: {
    workOrderId: string;
    onActivity?: (active: boolean) => void;
}) {
    // WO-scoped, unlike `usePendingFpis` which is tenant-wide. Every status, so a
    // step whose latest first piece FAILED shows as held — after a fail the pending
    // card used to vanish and nothing said the run was stopped.
    const { data, isLoading } = useFpiRecords({
        work_order: workOrderId,
        ordering: "-created_at",
        limit: 200,
    });
    const startNew = useFpiGetOrCreate();
    const acknowledge = useAcknowledgeFpi();
    const canSignOff = usePermissionSet().has("sign_off_fpi");
    const [signing, setSigning] = useState<{ row: FpiRow; verdict: FpiVerdict } | null>(null);

    // The latest record per step decides: PENDING → waiting on QA; FAILED → held.
    const latestByStep = new Map<string, FpiRow>();
    for (const r of data?.results ?? []) {
        const key = String(r.step ?? "");
        if (!latestByStep.has(key)) latestByStep.set(key, r);
    }
    const rows: FpiRow[] = [...latestByStep.values()].filter((r) => r.status === "PENDING");
    const held: FpiRow[] = [...latestByStep.values()].filter((r) => r.status === "FAILED");
    useReportActivity(rows.length + held.length > 0, onActivity);

    if (isLoading) {
        return (
            <div className="flex items-center gap-2 rounded-lg border p-4 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Checking first-piece
                inspections…
            </div>
        );
    }

    // Self-hiding: a WO with no pending or held FPI shouldn't occupy space on Control.
    if (rows.length === 0 && held.length === 0) return null;

    return (
        <>
            {held.map((r) => (
                <div key={r.id} className="rounded-lg border-2 border-destructive/50 bg-destructive/10 p-4">
                    <div className="flex flex-wrap items-start gap-3">
                        <ShieldAlert className="mt-0.5 h-5 w-5 text-destructive" />
                        <div className="min-w-0 flex-1 space-y-1">
                            <p className="font-medium">
                                First piece failed at {r.step_info?.name ?? "this step"} — run held
                            </p>
                            <p className="text-sm text-muted-foreground">
                                No part moves past this step. Correct the setup, then start a new
                                first piece for inspection.
                                {r.inspected_by_info?.full_name ? ` Failed by ${r.inspected_by_info.full_name}.` : ""}
                            </p>
                            {r.notes && <p className="text-sm italic">“{r.notes}”</p>}
                        </div>
                        <Button size="sm" disabled={startNew.isPending}
                                onClick={() => startNew.mutate(
                                    { work_order: workOrderId, step: String(r.step),
                                      ...(r.equipment ? { equipment: String(r.equipment) } : {}) },
                                    {
                                        onSuccess: () => toast.success("New first piece started — it's waiting on QA once inspected."),
                                        onError: (e) => toast.error(apiErrorMessage(e) ?? "Could not start a new first piece"),
                                    })}>
                            Start a new first piece
                        </Button>
                    </div>
                </div>
            ))}
            {rows.length > 0 && (
        <>
            <div className="rounded-lg border-2 border-amber-500/50 bg-amber-500/10 p-4">
                <div className="mb-3 flex items-center gap-2">
                    <ShieldAlert className="h-5 w-5 text-amber-600" />
                    <h3 className="font-medium">
                        First piece waiting on QA
                        <Badge variant="secondary" className="ml-2">{rows.length}</Badge>
                    </h3>
                </div>
                <p className="mb-3 text-sm text-muted-foreground">
                    No part moves past these steps until the first piece is bought off.
                </p>

                <div className="space-y-2">
                    {rows.map((row) => {
                        const ackName = row.acknowledged_by_info?.full_name
                            || row.acknowledged_by_info?.username
                            || "QA";
                        return (
                            <div
                                key={row.id}
                                className="flex flex-wrap items-center gap-3 rounded-md border bg-background p-3"
                            >
                                <div className="min-w-0 flex-1">
                                    <p className="font-medium">
                                        {row.step_info?.name ?? "Step"}
                                    </p>
                                    <p className="text-sm text-muted-foreground">
                                        {row.designated_part_info?.erp_id
                                            ?? "first piece designated at sign-off"}
                                        {row.equipment_info?.name
                                            ? ` · ${row.equipment_info.name}`
                                            : ""}
                                    </p>
                                </div>

                                {row.acknowledged_at ? (
                                    <Badge variant="outline">Seen by {ackName}</Badge>
                                ) : canSignOff && (
                                    // Acknowledging is the inspector's word that they're coming;
                                    // the server takes it only from someone who can sign off.
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        disabled={acknowledge.isPending}
                                        onClick={() =>
                                            acknowledge.mutate(row.id, {
                                                onSuccess: () =>
                                                    toast.success(
                                                        "Acknowledged — the operator sees you're on it."),
                                                onError: () =>
                                                    toast.error("Could not acknowledge."),
                                            })
                                        }
                                    >
                                        I'm on it
                                    </Button>
                                )}

                                <Button size="sm" onClick={() => setSigning({ row, verdict: "PASS" })}>
                                    {canSignOff ? "Sign off" : "Get QA sign-off"}
                                </Button>
                                {/* Fail and waive sit beside pass, under the same SoD and
                                    assurance rules (the co-sign path when you can't sign). */}
                                <Button size="sm" variant="destructive" onClick={() => setSigning({ row, verdict: "FAIL" })}>
                                    Fail
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => setSigning({ row, verdict: "WAIVE" })}>
                                    Waive
                                </Button>
                            </div>
                        );
                    })}
                </div>
            </div>

        </>
            )}
            {signing && (
                <FpiSignOffDialog
                    key={`${signing.row.id}-${signing.verdict}`}
                    open={Boolean(signing)}
                    onOpenChange={(v) => !v && setSigning(null)}
                    fpiId={signing.row.id}
                    canSignOff={canSignOff}
                    assurance={signing.row.step_info?.qa_signoff_assurance}
                    partLabel={signing.row.designated_part_info?.erp_id ?? null}
                    verdict={signing.verdict}
                    onSigned={() => setSigning(null)}
                />
            )}
        </>
    );
}
