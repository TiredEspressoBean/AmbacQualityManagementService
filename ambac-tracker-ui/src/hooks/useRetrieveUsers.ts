import {useQuery, type UseQueryOptions} from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveUsers(queries: Parameters<typeof api.api_User_list>[0],
                                 options?: Omit<
                                     UseQueryOptions<
                                         Awaited<ReturnType<typeof api.api_User_list>>,
                                         Error
                                     >,
                                     "queryKey" | "queryFn"
                                 >) {
    return useQuery({
        queryKey: ["Users", queries],
        queryFn: () => api.api_User_list(queries),
        ...options
    });
}
