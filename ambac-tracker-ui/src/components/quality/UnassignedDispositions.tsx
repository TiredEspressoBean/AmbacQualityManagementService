/**
 * NCRs nobody has taken yet — the QA queue, one row per NCR. A failure raises its NCR
 * unowned (user decision 2026-10-20); taking it here makes you its owner: its
 * containment, its CAPA call, and every decision under it not yet closed (user go
 * 2026-11-18). Taking needs what taking a decision always did
 * (change_quarantinedisposition). Hidden when the queue is empty.
 */
import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { toast } from "sonner";

import { api } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { invalidateAfterNcrChange } from "@/hooks/ncrs";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { Button } from "@/components/ui/button";
import type { Schema } from "@/lib/api/types";

export const unassignedNcrsOptions = () =>
    queryOptions({
        queryKey: ["ncrs", "unassigned"] as const,
        queryFn: () => api.api_NCRs_list({
            queries: { assigned_to__isnull: true, state: "OPEN", ordering: "created_at", limit: 25 },
        }),
        select: (d) => d.results ?? [],
    });

/** What an NCR covers, in a few words: its part, "3 parts", or its lot. */
export const ncrCovers = (n: Schema<"NCR">) => {
    const parts = n.members.filter((m) => m.part_id);
    if (parts.length === 1) return parts[0]!.erp_id;
    if (parts.length > 1) return `${parts.length} parts`;
    const lot = n.members.find((m) => m.lot_number);
    return lot ? `Lot ${lot.lot_number}` : null;
};

export function UnassignedNcrs({ userPk }: { userPk: number }) {
    const qc = useQueryClient();
    const canTake = usePermissionSet().has("change_quarantinedisposition");
    const { data: rows = [] } = useQuery(unassignedNcrsOptions());

    const take = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: (id: string) => api.api_NCRs_assign_create({ assigned_to: userPk }, { params: { id } }),
        onSuccess: (ncr) => {
            toast.success(`${ncr.ncr_number} is yours — with its decisions.`);
            void invalidateAfterNcrChange(qc);
        },
        onError: (e) => toast.error(apiErrorMessage(e) ?? "Could not take the NCR"),
    });

    if (rows.length === 0) return null;

    return (
        <div className="mt-3">
            <div className="text-xs text-muted-foreground">
                NCRs nobody has taken — raised by a failed inspection or a part held at MRB:
            </div>
            {rows.map((n) => (
                <div key={n.id} className="mt-1 flex items-center gap-3 rounded-lg border border-dashed p-2.5">
                    <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <Link to="/quality/ncrs/$ncrId" params={{ ncrId: String(n.id) }} className="min-w-0 flex-1">
                        <span className="block truncate text-sm">
                            {n.todo.at_mrb && (
                                <span className="mr-1.5 rounded bg-destructive/10 px-1.5 py-0.5 text-xs font-medium text-destructive">MRB</span>
                            )}
                            {[n.ncr_number, ncrCovers(n), n.work_order_erp_id, n.severity_display, n.description]
                                .filter(Boolean).join(" · ")}
                        </span>
                    </Link>
                    {canTake && (
                        <Button size="sm" variant="outline" className="h-8 shrink-0"
                                disabled={take.isPending} onClick={() => take.mutate(String(n.id))}>
                            Take it
                        </Button>
                    )}
                </div>
            ))}
        </div>
    );
}
