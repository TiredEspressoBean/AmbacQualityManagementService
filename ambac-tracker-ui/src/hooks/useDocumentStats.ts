import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export interface DocumentStats {
    total: number;
    pending_approval: number;
    needs_my_approval: number;
    my_uploads: number;
    recent_count: number;
    by_classification: Record<string, number>;
}

export function useDocumentStats() {
    return useQuery({
        queryKey: ["documents", "stats"],
        queryFn: () => api.api_Documents_stats_retrieve() as Promise<DocumentStats>,
    });
}
