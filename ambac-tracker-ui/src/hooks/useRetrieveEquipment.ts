import { api } from "@/lib/api/generated.ts"
import {useQuery} from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

type EquipmentsResponse = Schema<"Equipments">;

export function useRetrieveEquipment(
    query: Parameters<typeof api.api_Equipment_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery<EquipmentsResponse>({
        queryKey: ["equipment", query],
        queryFn: () => api.api_Equipment_retrieve(query) as Promise<EquipmentsResponse>,
        enabled: options?.enabled ?? true,
    });
}