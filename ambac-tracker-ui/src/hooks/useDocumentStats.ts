import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export interface DocumentStats {
    total: number;
    pending_approval: number;
    needs_my_approval: number;
    my_uploads: number;
    recent_count: number;
    by_classification: Record<string, number>;
}

export const documentStatsOptions = () => queryOptions({
    queryKey: ["documents", "stats"] as const,
    queryFn: () => api.api_Documents_stats_retrieve() as unknown as Promise<DocumentStats>,
});

export function useDocumentStats() {
    return useQuery({ ...documentStatsOptions() });
}
