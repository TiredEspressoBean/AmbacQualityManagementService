import { api } from "@/lib/api/generated.ts"
import {useQuery} from "@tanstack/react-query";

export function useRetrieveErrorType(
    query: Parameters<typeof api.api_Error_types_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["error-type", query],
        queryFn: () => api.api_Error_types_retrieve(query),
        enabled: options?.enabled ?? true,
    });
}