import {useQuery, type UseQueryOptions} from "@tanstack/react-query"
import {api} from "@/lib/api/generated.ts"

export function useRetrieveWorkOrders (queries: Parameters<typeof api.api_WorkOrders_list>[0],
                                       options?: Omit<
                                           UseQueryOptions<
                                               Awaited<ReturnType<typeof api.api_WorkOrders_list>>,
                                               Error
                                           >,
                                           "queryKey" | "queryFn"
                                       >) {
    return useQuery({
        queryKey: ["work_orders", queries],
        queryFn: () => {
            return api.api_WorkOrders_list(queries);
        },
        ...options,
    });
};