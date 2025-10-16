import { api } from "@/lib/api/generated.ts"
import {useQuery} from "@tanstack/react-query";

export function useRetrieveQuarantineDispositions(
    query: Parameters<typeof api.api_QuarantineDispositions_list>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["quarantine-dispositions", query],
        queryFn: () => api.api_QuarantineDispositions_list(query),
        enabled: options?.enabled ?? true,
    });
}