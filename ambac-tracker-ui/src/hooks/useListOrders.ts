import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api, type CustomerOrder } from "@/lib/api/generated.ts";

export function useRetrieveOrders(
  queries?: Parameters<typeof api.api_Orders_list>[0],
  options?: Omit<
    UseQueryOptions<CustomerOrder[], Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<CustomerOrder[], Error>({
    queryKey: ["orders", queries],
    queryFn: async () => {
      const response = await api.api_Orders_list(queries);
      return response.results;
    },
    ...options,
  });
}