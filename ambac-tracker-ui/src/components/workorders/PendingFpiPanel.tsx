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

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FpiSignOffDialog } from "@/components/fpi-sign-off-dialog";
import { useFpiRecords } from "@/hooks/useFpiRecords";
import { useAcknowledgeFpi } from "@/hooks/useAcknowledgeFpi";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { useReportActivity } from "@/hooks/useReportActivity";

type FpiRow = {
    id: string;
    step_info?: { id: string; name?: string | null } | null;
    designated_part_info?: { id: string; erp_id?: string | null } | null;
    equipment_info?: { id: string; name?: string | null } | null;
    acknowledged_by_info?: { username?: string | null; full_name?: string | null } | null;
    acknowledged_at?: string | null;
};

export function PendingFpiPanel({ workOrderId, onActivity }: {
    workOrderId: string;
    onActivity?: (active: boolean) => void;
}) {
    // WO-scoped, unlike `usePendingFpis` which is tenant-wide. `work_order` is
    // already in FPIRecordViewSet.filterset_fields, so no new endpoint.
    const { data, isLoading } = useFpiRecords({
        work_order: workOrderId,
        status: "PENDING",
    } as never);
    const acknowledge = useAcknowledgeFpi();
    const canSignOff = usePermissionSet().has("sign_off_fpi");
    const [signing, setSigning] = useState<FpiRow | null>(null);

    // The `*_info` fields are declared DictField in the serializer, so the
    // generated client types them as loose records — narrow them here.
    const rows: FpiRow[] = (data as unknown as { results?: FpiRow[] } | undefined)?.results ?? [];
    useReportActivity(rows.length > 0, onActivity);

    if (isLoading) {
        return (
            <div className="flex items-center gap-2 rounded-lg border p-4 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Checking first-piece
                inspections…
            </div>
        );
    }

    // Self-hiding: a WO with no pending FPI shouldn't occupy space on Control.
    if (rows.length === 0) return null;

    return (
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
                                            ?? "first piece not yet designated"}
                                        {row.equipment_info?.name
                                            ? ` · ${row.equipment_info.name}`
                                            : ""}
                                    </p>
                                </div>

                                {row.acknowledged_at ? (
                                    <Badge variant="outline">Seen by {ackName}</Badge>
                                ) : (
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

                                <Button size="sm" onClick={() => setSigning(row)}>
                                    {canSignOff ? "Sign off" : "Get QA sign-off"}
                                </Button>
                            </div>
                        );
                    })}
                </div>
            </div>

            {signing && (
                <FpiSignOffDialog
                    open={Boolean(signing)}
                    onOpenChange={(v) => !v && setSigning(null)}
                    fpiId={signing.id}
                    canSignOff={canSignOff}
                    partLabel={signing.designated_part_info?.erp_id ?? null}
                    onSigned={() => setSigning(null)}
                />
            )}
        </>
    );
}
