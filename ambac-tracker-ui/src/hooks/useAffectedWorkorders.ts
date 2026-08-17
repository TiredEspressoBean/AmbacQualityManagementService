import { useQuery } from "@tanstack/react-query";

/**
 * Fetch the per-WO impact summary for a PCO's migration picker.
 *
 * Raw fetch (not Zodios) because the response shape is an ad-hoc
 * `{results: [...]}` not declared in the serializer registry — the
 * @action endpoint just returns a list of dicts straight from the
 * impact-analysis service.
 */
export type StrandedPart = {
    part_id: string;
    wo_id: string;
    step_id: string;
    step_name: string;
};

export type AffectedWorkorderRow = {
    wo_id: string;
    erp_id: string;
    status: string;
    priority: number;
    quantity: number;
    total_parts: number;
    affected_parts: number;
    /** Parts whose step survives the migration (auto-port). Present when the
     * picker is asked to classify against the new version. */
    portable_count?: number;
    /** Parts at a step REMOVED in the new version — each needs a resolution. */
    stranded?: StrandedPart[];
};

/** A surviving step in the new version — a RELOCATE target. */
export type AvailableStep = { id: string; name: string };

export type AffectedWorkorders = {
    rows: AffectedWorkorderRow[];
    availableSteps: AvailableStep[];
};

export function useAffectedWorkorders(pcoId: string | undefined, enabled = true) {
    return useQuery<AffectedWorkorders>({
        queryKey: ["pco-affected-workorders", pcoId] as const,
        enabled: !!pcoId && enabled,
        queryFn: async () => {
            const r = await fetch(
                `/api/process-change-orders/${pcoId}/affected-workorders/`,
                { credentials: "include" },
            );
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const j = (await r.json()) as {
                results?: AffectedWorkorderRow[];
                available_steps?: AvailableStep[];
            };
            return { rows: j.results ?? [], availableSteps: j.available_steps ?? [] };
        },
    });
}
