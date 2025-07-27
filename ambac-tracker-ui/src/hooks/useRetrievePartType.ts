import { api } from "@/lib/api/generated.ts"
import {useQuery} from "@tanstack/react-query";

export function useRetrievePartType(
    query: Parameters<typeof api.api_PartTypes_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["parttype", query],
        queryFn: () => api.api_PartTypes_retrieve(query),
        enabled: options?.enabled ?? true,
    });
}