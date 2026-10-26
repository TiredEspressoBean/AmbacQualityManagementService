import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { useAuthUser } from "@/hooks/useAuthUser";
import { Button } from "@/components/ui/button";
import { CorrectTimeEntryButton } from "@/components/scheduling/CorrectTimeEntryButton";

/** Day after an ISO date, so the range's last day is included. */
const dayAfter = (isoDate: string) => {
    const d = new Date(`${isoDate}T00:00:00`);
    d.setDate(d.getDate() + 1);
    return d.toISOString();
};

const pendingTimeOptions = (start: string, end: string) =>
    queryOptions({
        queryKey: ["time-entries", "awaiting-approval", { start, end }] as const,
        queryFn: () => api.api_TimeEntries_list({
            queries: {
                approved: false,
                end_time__isnull: false,
                start_time__gte: new Date(`${start}T00:00:00`).toISOString(),
                start_time__lt: dayAfter(end),
                ordering: "start_time",
                limit: 500,
            },
        }),
    });

/**
 * Finished time entries in the period that nobody has approved yet, for a shift lead or
 * production manager to sign off (`approve_timeentry`). Your own entries are listed but
 * can't be approved by you — someone else signs your time.
 */
export function TimeApprovalCard({ start, end }: { start: string; end: string }) {
    const queryClient = useQueryClient();
    const { data: me } = useAuthUser();
    const { data, isLoading } = useQuery(pendingTimeOptions(start, end));
    const entries = data?.results ?? [];
    const approvable = entries.filter((e) => e.user !== me?.pk);

    const approve = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: (id: string) => api.api_TimeEntries_approve_create(undefined, {
            params: { id }, headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
        }),
        onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't approve the entry"),
    });

    const approveIds = async (ids: string[]) => {
        let done = 0;
        for (const id of ids) {
            try { await approve.mutateAsync(id); done += 1; } catch { /* toasted */ }
        }
        if (done) toast.success(`Approved ${done} time entr${done === 1 ? "y" : "ies"}`);
        queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "time-entries" });
    };

    return (
        <div className="rounded-md border">
            <div className="flex items-center justify-between gap-3 border-b p-3">
                <div>
                    <div className="font-medium">Awaiting approval</div>
                    <div className="text-xs text-muted-foreground">
                        {isLoading ? "Loading…" : `${entries.length} finished entr${entries.length === 1 ? "y" : "ies"} not yet approved in this period`}
                    </div>
                </div>
                <Button size="sm" disabled={approvable.length === 0 || approve.isPending}
                        onClick={() => approveIds(approvable.map((e) => e.id))}>
                    Approve all{approvable.length ? ` (${approvable.length})` : ""}
                </Button>
            </div>
            {entries.length > 0 && (
                <table className="w-full text-sm">
                    <thead className="bg-muted/40 text-left text-xs text-muted-foreground">
                        <tr>
                            <th className="p-2">Operator</th>
                            <th className="p-2">Type</th>
                            <th className="p-2">Work order</th>
                            <th className="p-2">Started</th>
                            <th className="p-2 text-right">Hours</th>
                            <th className="p-2" />
                        </tr>
                    </thead>
                    <tbody>
                        {entries.map((e) => {
                            const own = e.user === me?.pk;
                            return (
                                <tr key={e.id} className="border-t">
                                    <td className="p-2">{e.user_name ?? "—"}</td>
                                    <td className="p-2 text-xs">{(e.entry_type ?? "").replace(/_/g, " ").toLowerCase()}</td>
                                    <td className="p-2 font-mono text-xs">{e.work_order_erp_id ?? "—"}</td>
                                    <td className="p-2 text-xs">{new Date(e.start_time).toLocaleString()}</td>
                                    <td className="p-2 text-right tabular-nums">{e.duration_hours != null ? e.duration_hours.toFixed(2) : "—"}</td>
                                    <td className="p-2 text-right">
                                        {own ? (
                                            <span className="text-xs text-muted-foreground">Your time</span>
                                        ) : (
                                            <>
                                                <CorrectTimeEntryButton entry={e} />
                                                <Button size="sm" variant="ghost" disabled={approve.isPending}
                                                        onClick={() => approveIds([e.id])}>
                                                    Approve
                                                </Button>
                                            </>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            )}
        </div>
    );
}
