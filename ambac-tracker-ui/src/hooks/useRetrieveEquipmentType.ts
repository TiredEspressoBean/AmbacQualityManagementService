import { api } from "@/lib/api/generated.ts"
import {useQuery} from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

type EquipmentTypeResponse = Schema<"EquipmentType">;

export function useRetrieveEquipmentType(
    query: Parameters<typeof api.api_Equipment_types_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery<EquipmentTypeResponse>({
        queryKey: ["equipment", query],
        queryFn: () => api.api_Equipment_types_retrieve(query) as Promise<EquipmentTypeResponse>,
        enabled: options?.enabled ?? true,
    });
}