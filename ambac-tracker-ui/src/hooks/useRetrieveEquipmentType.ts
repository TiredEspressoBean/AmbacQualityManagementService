import { api } from "@/lib/api/generated.ts"
import {useQuery} from "@tanstack/react-query";

export function useRetrieveEquipmentType(
    query: Parameters<typeof api.api_Equipment_types_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["equipment", query],
        queryFn: () => api.api_Equipment_types_retrieve(query),
        enabled: options?.enabled ?? true,
    });
}