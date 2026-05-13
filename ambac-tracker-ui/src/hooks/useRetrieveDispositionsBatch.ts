import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";

export const retrieveDispositionsBatchOptions = (ids: string[]) => queryOptions({
    queryKey: ["dispositions-batch", ids] as const,
    queryFn: async () => {
        if (ids.length === 0) return [];
        return Promise.all(ids.map((id) => api.api_QuarantineDispositions_retrieve({ params: { id } })));
    },
});

export const useRetrieveDispositionsBatch = (ids: string[]) => {
    return useQuery({
        ...retrieveDispositionsBatchOptions(ids),
        enabled: ids.length > 0,
    });
};
