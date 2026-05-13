import { api } from "@/lib/api/generated.ts"
import {useQuery, queryOptions} from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

type PartTypesResponse = Schema<"PartTypes">;

export const retrievePartTypeOptions = (query: Parameters<typeof api.api_PartTypes_retrieve>[0]) => queryOptions({
    queryKey: ["parttype", query] as const,
    queryFn: () => api.api_PartTypes_retrieve(query) as Promise<PartTypesResponse>,
});

export function useRetrievePartType(query: Parameters<typeof api.api_PartTypes_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...retrievePartTypeOptions(query), enabled: options?.enabled ?? true });
}