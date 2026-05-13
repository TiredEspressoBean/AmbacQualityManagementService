import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

export type RecentDocument = Schema<"Documents">;

type PaginatedDocuments = Schema<"PaginatedDocumentsList">;

export const recentDocumentsOptions = () => queryOptions({
    queryKey: ["documents", "recent"] as const,
    queryFn: () => api.api_Documents_recent_list() as Promise<PaginatedDocuments>,
    // Unwrap the paginated wrapper at the cache boundary so consumers get the array directly.
    select: (data) => data.results,
});

export function useRecentDocuments() {
    return useQuery({ ...recentDocumentsOptions() });
}
