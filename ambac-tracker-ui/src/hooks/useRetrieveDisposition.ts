import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

// Extend the strict spec type with the document attachment shape the API also returns
// (the OpenAPI schema records `documents` only on related serializers; the detail
// endpoint includes it in practice).
type DispositionDetail = Schema<"QuarantineDisposition"> & {
    documents?: { id: string; file_url: string; file_name: string }[];
    annotation_status?: { has_pending?: boolean; pending_count?: number } | null;
};

export const useRetrieveDisposition = (id: string | undefined) => {
    return useQuery<DispositionDetail>({
        queryKey: ["disposition", id],
        queryFn: () => api.api_QuarantineDispositions_retrieve({ params: { id: id! } }) as Promise<DispositionDetail>,
        enabled: !!id,
    });
};
