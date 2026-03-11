import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api, type CustomerOrder } from "@/lib/api/generated.ts";

// Extract queries type from Zodios endpoint
type OrdersListQueries = Parameters<typeof api.api_Orders_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_Orders_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveOrders(
  queries?: OrdersListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<CustomerOrder[], Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<CustomerOrder[], Error>({
    queryKey: ["orders", queries, config],
    queryFn: async () => {
      const response = await api.api_Orders_list(queries || config ? { queries, ...config } : undefined);
      return response.results;
    },
    ...options,
  });
}
