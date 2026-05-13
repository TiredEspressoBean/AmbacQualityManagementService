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

export const capaStatsOptions = () => queryOptions<CapaStats>({
    queryKey: ["capa-stats"] as const,
    queryFn: () => api.api_CAPAs_stats_retrieve() as Promise<CapaStats>,
    refetchInterval: 2 * 60 * 1000, // Poll every 2 minutes - actionable stats
});

export const useCapaStats = () => {
    return useQuery(capaStatsOptions());
};
