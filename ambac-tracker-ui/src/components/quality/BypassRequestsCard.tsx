/**
 * Bypass requests waiting for a decision, for holders of approve_stepoverride (QA
 * Manager, Tenant Admin). Approving lets the part past that one block until the step's
 * override expiry and re-runs its advancement at once; refusing records why. Nobody
 * decides their own request. Hidden when nothing is waiting.
 */
import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNowStrict } from "date-fns";
import { toast } from "sonner";

import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { useAuthUser } from "@/hooks/useAuthUser";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export const pendingBypassOptions = () =>
    queryOptions({
        queryKey: ["bypass-requests", "pending"] as const,
        queryFn: () => api.api_StepOverrides_list({ queries: { status: "PENDING", limit: 100 } }),
    });

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });

export function BypassRequestsCard() {
    const queryClient = useQueryClient();
    const { data: me } = useAuthUser();
    const { data } = useQuery(pendingBypassOptions());
    const [refusing, setRefusing] = useState<string | null>(null);
    const [refusal, setRefusal] = useState("");
    const requests = data?.results ?? [];

    const done = (msg: string) => {
        toast.success(msg);
        setRefusing(null);
        setRefusal("");
        queryClient.invalidateQueries(pendingBypassOptions());
        queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "part-blockers" });
    };
    const approve = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: (id: string) => api.api_StepOverrides_approve_create({}, { params: { id }, headers: csrf() }),
        onSuccess: () => done("Bypass approved"),
        onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't approve the bypass"),
    });
    const refuse = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: (id: string) => api.api_StepOverrides_reject_create({ reason: refusal.trim() }, { params: { id }, headers: csrf() }),
        onSuccess: () => done("Bypass refused"),
        onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't refuse the bypass"),
    });

    if (requests.length === 0) return null;

    return (
        <div className="rounded-xl border bg-card p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Bypass requests ({requests.length})
            </div>
            <ul className="mt-2 divide-y">
                {requests.map((r) => {
                    const info = r.step_execution_info as { part_id?: string | null; part_erp_id?: string | null; step_name?: string | null } | null;
                    const requester = r.requested_by_info as { full_name?: string; username?: string } | null;
                    const own = r.requested_by === me?.pk;
                    const busy = approve.isPending || refuse.isPending;
                    return (
                        <li key={r.id} className="space-y-2 py-2.5 text-sm">
                            <div className="flex flex-wrap items-start gap-2">
                                <div className="min-w-0 flex-1">
                                    <div>
                                        <span className="font-medium">{r.block_type_display}</span>
                                        {" · "}
                                        {info?.part_id ? (
                                            <Link to="/details/$model/$id" params={{ model: "parts", id: info.part_id }} className="font-mono underline-offset-2 hover:underline">
                                                {info.part_erp_id}
                                            </Link>
                                        ) : <span className="font-mono">{info?.part_erp_id ?? "—"}</span>}
                                        {info?.step_name && <span className="text-muted-foreground"> at {info.step_name}</span>}
                                    </div>
                                    <div className="italic">“{r.reason}”</div>
                                    <div className="text-xs text-muted-foreground">
                                        {requester?.full_name || requester?.username || "Someone"} · {formatDistanceToNowStrict(new Date(r.requested_at), { addSuffix: true })}
                                    </div>
                                </div>
                                {own ? (
                                    <span className="text-xs text-muted-foreground">Your request — someone else decides it</span>
                                ) : refusing !== r.id && (
                                    <div className="flex gap-2">
                                        <Button size="sm" disabled={busy} onClick={() => approve.mutate(r.id)}>Approve</Button>
                                        <Button size="sm" variant="outline" disabled={busy} onClick={() => setRefusing(r.id)}>Refuse</Button>
                                    </div>
                                )}
                            </div>
                            {refusing === r.id && (
                                <div className="flex flex-wrap gap-2">
                                    <Input className="min-w-0 flex-1" placeholder="Why it's refused" value={refusal}
                                           onChange={(e) => setRefusal(e.target.value)} autoFocus />
                                    <Button size="sm" variant="destructive" disabled={!refusal.trim() || busy}
                                            onClick={() => refuse.mutate(r.id)}>Refuse</Button>
                                    <Button size="sm" variant="ghost" onClick={() => setRefusing(null)}>Cancel</Button>
                                </div>
                            )}
                        </li>
                    );
                })}
            </ul>
        </div>
    );
}
