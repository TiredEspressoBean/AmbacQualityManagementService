import { useQuery, type UseQueryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrievePartTypes (queries: Parameters<typeof api.api_PartTypes_list>[0],
                                      options?: Omit<
                                          UseQueryOptions<
                                              Awaited<ReturnType<typeof api.api_PartTypes_list>>,
                                              Error
                                          >,
                                          "queryKey" | "queryFn"
                                      >) {
    return useQuery({
        queryKey: ["parttypes", queries],
        queryFn: () => api.api_PartTypes_list(queries),
        ...options
    });
};