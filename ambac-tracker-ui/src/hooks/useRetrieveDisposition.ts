import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

type RetrieveDispositionResponse = Awaited<ReturnType<typeof api.api_QuarantineDispositions_retrieve>>;

export const useRetrieveDisposition = (id: string | undefined) => {
    return useQuery<RetrieveDispositionResponse>({
        queryKey: ["disposition", id],
        queryFn: () => api.api_QuarantineDispositions_retrieve({ params: { id: id! } }),
        enabled: !!id,
    });
};
