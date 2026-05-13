import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

// Extract queries type from Zodios endpoint
type CustomersListQueries = Parameters<typeof api.api_Customers_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_Customers_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const retrieveCustomersOptions = (queries?: CustomersListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["customers", queries, config] as const,
  queryFn: () => api.api_Customers_list(
    (queries || config ? { queries, ...config } : undefined) as never,
  ),
});

export function useRetrieveCustomers(
  queries?: CustomersListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof retrieveCustomersOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...retrieveCustomersOptions(queries, config),
    ...options,
  });
}
