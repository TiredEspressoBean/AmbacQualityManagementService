/**
 * Dispositions nobody has taken yet — the QA queue. A failed report opens its
 * disposition unassigned (user decision 2026-10-20); QA takes it from here and it moves
 * to "My dispositions". Taking one is an edit of its assignee
 * (change_quarantinedisposition). Hidden when the queue is empty.
 */
import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { toast } from "sonner";

import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { Button } from "@/components/ui/button";

export const unassignedDispositionsOptions = () =>
    queryOptions({
        queryKey: ["dispositions", "unassigned"] as const,
        queryFn: () => api.api_QuarantineDispositions_list({
            queries: { assigned_to__isnull: true, limit: 25 },
        }),
        select: (d) => (d.results ?? []).filter((r) => r.current_state !== "CLOSED"),
    });

export function UnassignedDispositions({ userPk }: { userPk: number }) {
    const qc = useQueryClient();
    const canTake = usePermissionSet().has("change_quarantinedisposition");
    const { data: rows = [] } = useQuery(unassignedDispositionsOptions());

    const take = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: (id: string) => api.api_QuarantineDispositions_partial_update(
            { assigned_to: userPk },
            { params: { id }, headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" } },
        ),
        onSuccess: () => {
            toast.success("Taken — it's in your dispositions.");
            qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "dispositions" || q.queryKey[0] === "my-dispositions" });
        },
        onError: (e) => toast.error(apiErrorMessage(e) ?? "Could not take the disposition"),
    });

    if (rows.length === 0) return null;

    return (
        <div className="mt-3">
            <div className="text-xs text-muted-foreground">
                Unassigned dispositions — opened by a failed inspection or a part held at MRB; nobody has taken them:
            </div>
            {rows.map((d) => (
                <div key={d.id} className="mt-1 flex items-center gap-3 rounded-lg border border-dashed p-2.5">
                    <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <Link to="/production/dispositions/$id/edit" params={{ id: d.id }} className="min-w-0 flex-1">
                        <span className="block truncate text-sm">
                            {/* An MRB hold: a visit cap or a failed check sent the part there. */}
                            {d.escalated_from_step && (
                                <span className="mr-1.5 rounded bg-destructive/10 px-1.5 py-0.5 text-xs font-medium text-destructive">MRB</span>
                            )}
                            {d.disposition_number}{d.part_erp_id ? ` · ${d.part_erp_id}` : ""}{d.work_order_erp_id ? ` · ${d.work_order_erp_id}` : ""}{d.description ? ` · ${d.description}` : ""}
                        </span>
                    </Link>
                    {canTake && (
                        <Button size="sm" variant="outline" className="h-8 shrink-0"
                                disabled={take.isPending} onClick={() => take.mutate(d.id)}>
                            Take it
                        </Button>
                    )}
                </div>
            ))}
        </div>
    );
}
