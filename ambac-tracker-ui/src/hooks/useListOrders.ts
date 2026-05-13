import { useQuery, queryOptions } from "@tanstack/react-query";
import { api, type CustomerOrder } from "@/lib/api/generated.ts";
import type { operations } from "@/lib/api/generated-types";

type OrdersListQueries = NonNullable<operations["api_Orders_list"]["parameters"]["query"]>;

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const retrieveOrdersOptions = (queries?: OrdersListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["orders", queries, config] as const,
  queryFn: async () => {
    const response = await api.api_Orders_list(
      (queries || config ? { queries, ...config } : undefined) as never,
    );
    // eslint-disable-next-line local/no-double-cast-via-unknown -- generated api_Orders_list returns a union that doesn't expose .results; runtime is paginated
    return (response as unknown as { results: CustomerOrder[] }).results;
  },
});

export function useRetrieveOrders(
  queries?: OrdersListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof retrieveOrdersOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...retrieveOrdersOptions(queries, config),
    ...options,
  });
}
