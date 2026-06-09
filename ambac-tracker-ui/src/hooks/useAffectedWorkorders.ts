import { useQuery } from "@tanstack/react-query";

/**
 * Fetch the per-WO impact summary for a PCO's migration picker.
 *
 * Raw fetch (not Zodios) because the response shape is an ad-hoc
 * `{results: [...]}` not declared in the serializer registry — the
 * @action endpoint just returns a list of dicts straight from the
 * impact-analysis service.
 */
export type AffectedWorkorderRow = {
    wo_id: string;
    erp_id: string;
    status: string;
    priority: number;
    quantity: number;
    total_parts: number;
    affected_parts: number;
};

export function useAffectedWorkorders(pcoId: string | undefined, enabled = true) {
    return useQuery({
        queryKey: ["pco-affected-workorders", pcoId] as const,
        enabled: !!pcoId && enabled,
        queryFn: async () => {
            const r = await fetch(
                `/api/process-change-orders/${pcoId}/affected-workorders/`,
                { credentials: "include" },
            );
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const j = (await r.json()) as { results?: AffectedWorkorderRow[] };
            return j.results ?? [];
        },
    });
}
