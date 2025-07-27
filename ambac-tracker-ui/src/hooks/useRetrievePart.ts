import { api } from "@/lib/api/generated.ts"
import {useQuery} from "@tanstack/react-query";

export function useRetrievePart(
    query: Parameters<typeof api.api_Parts_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["parts", query],
        queryFn: () => api.api_Parts_retrieve(query),
        enabled: options?.enabled ?? true,
    });
}