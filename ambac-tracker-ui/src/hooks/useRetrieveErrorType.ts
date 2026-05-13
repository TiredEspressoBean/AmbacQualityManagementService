import { api } from "@/lib/api/generated.ts"
import {useQuery, queryOptions} from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

type QualityErrorsListResponse = Schema<"QualityErrorsList">;

export const retrieveErrorTypeOptions = (query: Parameters<typeof api.api_Error_types_retrieve>[0]) => queryOptions({
    queryKey: ["error-type", query] as const,
    queryFn: () => api.api_Error_types_retrieve(query) as Promise<QualityErrorsListResponse>,
});

export function useRetrieveErrorType(query: Parameters<typeof api.api_Error_types_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...retrieveErrorTypeOptions(query), enabled: options?.enabled ?? true });
}