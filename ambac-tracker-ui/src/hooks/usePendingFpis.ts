/** Pending first-piece inspections — the queue-jumper banner's data. Carries
 *  the acknowledged_by/at state the inbox aggregate doesn't (sent → seen →
 *  verdict; a machine and operator may be idle behind each of these). */
import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export type PendingFpi = {
    id: string;
    work_order_info?: { id: string; erp_id?: string | null } | null;
    step_info?: { id: string; name?: string | null } | null;
    part_type_info?: { id: string; name?: string | null } | null;
    equipment_info?: { id: string; name?: string | null } | null;
    designated_part_info?: { id: string; erp_id?: string | null } | null;
    acknowledged_by_info?: { username?: string | null; first_name?: string | null } | null;
    acknowledged_at?: string | null;
    created_at?: string | null;
};

export const pendingFpisOptions = () =>
    queryOptions({
        queryKey: ["pendingFpis"] as const,
        queryFn: () =>
            api.api_FPIRecords_list({
                queries: { status: "PENDING", limit: 10 },
            }) as Promise<{ results?: PendingFpi[] }>,
        staleTime: 15_000,
        select: (resp) => resp.results ?? [],
    });

export function usePendingFpis() {
    return useQuery(pendingFpisOptions());
}
