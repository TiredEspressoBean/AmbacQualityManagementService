import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type OrdersListQueries = NonNullable<operations["api_Orders_list"]["parameters"]["query"]>;
type OrdersListResponse = components["schemas"]["PaginatedOrdersList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveOrders(
  queries?: OrdersListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<OrdersListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<OrdersListResponse, Error>({
    queryKey: ["order", queries, config],
    queryFn: () =>
      api.api_Orders_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<OrdersListResponse>,
    ...options,
  });
}
