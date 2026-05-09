import { api } from "@/lib/api/generated.ts"
import {useQuery} from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

type PartTypesResponse = Schema<"PartTypes">;

export function useRetrievePartType(
    query: Parameters<typeof api.api_PartTypes_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery<PartTypesResponse>({
        queryKey: ["parttype", query],
        queryFn: () => api.api_PartTypes_retrieve(query) as Promise<PartTypesResponse>,
        enabled: options?.enabled ?? true,
    });
}