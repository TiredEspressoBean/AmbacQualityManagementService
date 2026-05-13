import { api } from "@/lib/api/generated.ts"
import {useQuery, queryOptions} from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

type EquipmentTypeResponse = Schema<"EquipmentType">;

export const retrieveEquipmentTypeOptions = (query: Parameters<typeof api.api_Equipment_types_retrieve>[0]) => queryOptions({
    queryKey: ["equipment", query] as const,
    queryFn: () => api.api_Equipment_types_retrieve(query) as Promise<EquipmentTypeResponse>,
});

export function useRetrieveEquipmentType(query: Parameters<typeof api.api_Equipment_types_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...retrieveEquipmentTypeOptions(query), enabled: options?.enabled ?? true });
}