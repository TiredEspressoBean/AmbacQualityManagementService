import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

type Response = Awaited<ReturnType<typeof api.api_process_change_orders_affected_workorders_retrieve>>;

export type AffectedWorkorderRow = Response["results"][number];
export type StrandedPart = NonNullable<AffectedWorkorderRow["stranded"]>[number];
/** A surviving step in the new version — a RELOCATE target. */
export type AvailableStep = Response["available_steps"][number];

export type AffectedWorkorders = {
    rows: AffectedWorkorderRow[];
    availableSteps: AvailableStep[];
};

export const affectedWorkordersOptions = (pcoId: string | undefined) => queryOptions({
    queryKey: ["pco-affected-workorders", pcoId] as const,
    queryFn: async (): Promise<AffectedWorkorders> => {
        const r = await api.api_process_change_orders_affected_workorders_retrieve({
            params: { id: pcoId! },
        });
        return { rows: r.results, availableSteps: r.available_steps };
    },
});

export function useAffectedWorkorders(pcoId: string | undefined, enabled = true) {
    return useQuery({
        ...affectedWorkordersOptions(pcoId),
        enabled: !!pcoId && enabled,
    });
}
