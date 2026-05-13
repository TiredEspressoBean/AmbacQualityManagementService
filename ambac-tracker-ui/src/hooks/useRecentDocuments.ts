import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export interface RecentDocument {
    id: string;
    file_name: string;
    classification: string;
    version: string | null;
    upload_date: string;
    updated_at: string;
    uploaded_by: string;
    uploaded_by_name: string;
}

export const recentDocumentsOptions = () => queryOptions({
    queryKey: ["documents", "recent"] as const,
    queryFn: () => api.api_Documents_recent_retrieve() as unknown as Promise<RecentDocument[]>,
});

export function useRecentDocuments() {
    return useQuery({ ...recentDocumentsOptions() });
}
