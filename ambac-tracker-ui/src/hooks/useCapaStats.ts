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
    const hasFilters = Object.keys(queries).length > 0;
    return queryOptions<CapaStats>({
        queryKey: ["capa-stats", queries] as const,
        queryFn: () =>
            api.api_CAPAs_stats_retrieve(hasFilters ? ({ queries } as never) : undefined) as Promise<CapaStats>,
        refetchInterval: 2 * 60 * 1000, // Poll every 2 minutes - actionable stats
    });
};

export const useCapaStats = (filters: CapaStatsFilters = {}) => {
    return useQuery(capaStatsOptions(filters));
};
