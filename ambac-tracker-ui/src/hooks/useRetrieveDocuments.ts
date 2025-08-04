import {useQuery, type UseQueryOptions} from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveDocuments (queries: Parameters<typeof api.api_Documents_list>[0],
                                      options?: Omit<
                                          UseQueryOptions<
                                              Awaited<ReturnType<typeof api.api_Documents_list>>,
                                              Error
                                          >,
                                          "queryKey" | "queryFn"
                                      >) {
    return useQuery({
        queryKey: ["documents", queries],
        queryFn: () => api.api_Documents_list(queries),
        ...options
    });
};