import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

export type DocumentStats = Schema<"DocumentStatsResponse">;

export const documentStatsOptions = () => queryOptions({
    queryKey: ["documents", "stats"] as const,
    queryFn: () => api.api_Documents_stats_retrieve() as Promise<DocumentStats>,
});

export function useDocumentStats() {
    return useQuery({ ...documentStatsOptions() });
}
