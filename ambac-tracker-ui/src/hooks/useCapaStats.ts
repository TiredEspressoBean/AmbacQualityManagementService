import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";

export type CapaStats = {
    total: number;
    by_status: {
        OPEN: number;
        IN_PROGRESS: number;
        PENDING_VERIFICATION: number;
        CLOSED: number;
    };
    by_severity: {
        CRITICAL: number;
        MAJOR: number;
        MINOR: number;
    };
    overdue: number;
};

export type CapaStatsFilters = { supplier?: string; capa_type?: string };

export const capaStatsOptions = (filters: CapaStatsFilters = {}) => {
    const queries: Record<string, string> = {};
    if (filters.supplier) queries.supplier = filters.supplier;
    if (filters.capa_type) queries.capa_type = filters.capa_type;
    return queryOptions<CapaStats>({
        queryKey: ["capa-stats", queries] as const,
        // The emptiness check is inlined rather than hoisted to a `hasFilters`
        // const: it is derived entirely from `queries`, which is already in the
        // key, but the exhaustive-deps rule can't see through the derivation and
        // flagged it as a missing dependency.
        queryFn: () =>
            api.api_CAPAs_stats_retrieve(
                Object.keys(queries).length > 0 ? ({ queries }) : undefined,
            ) as Promise<CapaStats>,
        refetchInterval: 2 * 60 * 1000, // Poll every 2 minutes - actionable stats
    });
};

export const useCapaStats = (filters: CapaStatsFilters = {}) => {
    return useQuery(capaStatsOptions(filters));
};
