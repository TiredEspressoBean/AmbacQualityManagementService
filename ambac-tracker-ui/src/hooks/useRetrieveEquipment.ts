import { api } from "@/lib/api/generated.ts"
import {useQuery, queryOptions} from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

type EquipmentsResponse = Schema<"Equipments">;

export const retrieveEquipmentOptions = (query: Parameters<typeof api.api_Equipment_retrieve>[0]) => queryOptions({
    queryKey: ["equipment", query] as const,
    queryFn: () => api.api_Equipment_retrieve(query) as Promise<EquipmentsResponse>,
});

export function useRetrieveEquipment(query: Parameters<typeof api.api_Equipment_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...retrieveEquipmentOptions(query), enabled: options?.enabled ?? true });
}