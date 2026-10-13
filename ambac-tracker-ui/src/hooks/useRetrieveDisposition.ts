import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

// No `documents` here: the API never returns it (an optional field grafted on here
// let the page compile against nothing, and its Attached Documents card never
// rendered). A disposition's documents are read through EntityDocumentsEditor.
type DispositionDetail = Schema<"QuarantineDisposition"> & {
    annotation_status?: { has_pending?: boolean; pending_count?: number } | null;
};

export const retrieveDispositionOptions = (id: string | undefined) => queryOptions({
    queryKey: ["disposition", id] as const,
    queryFn: () => api.api_QuarantineDispositions_retrieve({ params: { id: id! } }) as Promise<DispositionDetail>,
});

export const useRetrieveDisposition = (id: string | undefined) => {
    return useQuery({
        ...retrieveDispositionOptions(id),
        enabled: !!id,
    });
};
