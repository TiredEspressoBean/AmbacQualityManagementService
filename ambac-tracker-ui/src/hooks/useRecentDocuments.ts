import { useQuery } from "@tanstack/react-query";
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

export function useRecentDocuments() {
    return useQuery({
        queryKey: ["documents", "recent"],
        queryFn: () => api.api_Documents_recent_retrieve() as Promise<RecentDocument[]>,
    });
}
