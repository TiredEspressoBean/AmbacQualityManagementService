import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveOrders(
  queries?: Parameters<typeof api.api_Orders_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_Orders_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["order", queries],
    queryFn: () => api.api_Orders_list(queries),
    ...options,
  });
}