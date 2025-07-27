import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveEquipments (queries: Parameters<typeof api.api_Equipment_list>[0]) {
    return useQuery({
        queryKey: ["equipments", queries],
        queryFn: () => api.api_Equipment_list(queries),
    });
};