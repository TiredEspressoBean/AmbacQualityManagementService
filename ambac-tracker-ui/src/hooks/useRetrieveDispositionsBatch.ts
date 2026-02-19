import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

type RetrieveDispositionResponse = Awaited<ReturnType<typeof api.api_QuarantineDispositions_retrieve>>;

export const useRetrieveDispositionsBatch = (ids: string[]) => {
    return useQuery<RetrieveDispositionResponse[]>({
        queryKey: ["dispositions-batch", ids],
        queryFn: async () => {
            if (ids.length === 0) return [];
            return Promise.all(ids.map((id) => api.api_QuarantineDispositions_retrieve({ id })));
        },
        enabled: ids.length > 0,
    });
};
