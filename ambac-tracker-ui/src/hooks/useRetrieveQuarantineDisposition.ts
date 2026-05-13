import { api } from "@/lib/api/generated.ts"
import {useQuery, queryOptions} from "@tanstack/react-query";

export const retrieveQuarantineDispositionOptions = (query: Parameters<typeof api.api_QuarantineDispositions_retrieve>[0]) => queryOptions({
    queryKey: ["quarantine-dispositions", query] as const,
    queryFn: () => api.api_QuarantineDispositions_retrieve(query),
});

export function useRetrieveQuarantineDisposition(query: Parameters<typeof api.api_QuarantineDispositions_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...retrieveQuarantineDispositionOptions(query), enabled: options?.enabled ?? true });
}