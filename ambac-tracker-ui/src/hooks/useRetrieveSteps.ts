import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveSteps(queries: Parameters<typeof api.api_Steps_list>[0],
                                 options?: Omit<
                                     UseQueryOptions<
                                         Awaited<ReturnType<typeof api.api_Steps_list>>,
                                         Error
                                     >,
                                     "queryKey" | "queryFn"
                                 >) {
    return useQuery({
        queryKey: ["steps", queries],
        queryFn: () => api.api_Steps_list(queries),
        ...options
    });
}
