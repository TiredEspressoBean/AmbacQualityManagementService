import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type OrdersListQueries = NonNullable<operations["api_Orders_list"]["parameters"]["query"]>;
type OrdersListResponse = components["schemas"]["PaginatedOrdersList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const ordersOptions = (queries?: OrdersListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["order", queries, config] as const,
    queryFn: () =>
      api.api_Orders_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<OrdersListResponse>,
  });

export const ordersMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "Orders", "Orders"] as const,
    queryFn: () => api.api_Orders_metadata_retrieve(),
  });

export function useRetrieveOrders(
  queries?: OrdersListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof ordersOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...ordersOptions(queries, config),
    ...options,
  });
}
