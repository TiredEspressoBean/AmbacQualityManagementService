import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useRetrieveGroups(
  queries?: Parameters<typeof api.api_Groups_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_Groups_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["groups", queries],
    queryFn: () => api.api_Groups_list(queries),
    ...options,
  });
}