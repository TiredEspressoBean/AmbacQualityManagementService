import {useQuery, type UseQueryOptions} from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveParts (queries: Parameters<typeof api.api_Parts_list>[0],
                                  options?: Omit<
                                      UseQueryOptions<
                                          Awaited<ReturnType<typeof api.api_Parts_list>>,
                                          Error
                                      >,
                                      "queryKey" | "queryFn"
                                  >) {
    return useQuery({
        queryKey: ["parts", queries],
        queryFn: () => api.api_Parts_list(queries),
            ...options
    });
};