import { api } from "@/lib/api/generated.ts"
import {useQuery} from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

type QualityErrorsListResponse = Schema<"QualityErrorsList">;

export function useRetrieveErrorType(
    query: Parameters<typeof api.api_Error_types_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery<QualityErrorsListResponse>({
        queryKey: ["error-type", query],
        queryFn: () => api.api_Error_types_retrieve(query) as Promise<QualityErrorsListResponse>,
        enabled: options?.enabled ?? true,
    });
}