import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveErrorTypes(
  queries?: Parameters<typeof api.api_Error_types_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_Error_types_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["error-type", queries],
    queryFn: () => api.api_Error_types_list(queries),
    ...options,
  });
}