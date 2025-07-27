import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveEquipmentTypes (queries: Parameters<typeof api.api_Equipment_types_list>[0]) {
    return useQuery({
        queryKey: ["equipment-types", queries],
        queryFn: () => api.api_Equipment_types_list(queries),
    });
};