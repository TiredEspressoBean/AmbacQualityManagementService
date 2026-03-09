import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

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

export const useCapaStats = () => {
    return useQuery<CapaStats>({
        queryKey: ["capa-stats"],
        queryFn: () => api.api_CAPAs_stats_retrieve() as Promise<CapaStats>,
        refetchInterval: 2 * 60 * 1000, // Poll every 2 minutes - actionable stats
    });
};
