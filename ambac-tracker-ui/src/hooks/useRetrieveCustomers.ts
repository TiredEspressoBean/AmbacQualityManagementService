import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

// Extract queries type from Zodios endpoint
// The `extends { queries?: infer Q }` form this used fell through -- the
// param is optional, so the check failed and Q resolved to the whole config
// object rather than the query shape. Indexing it directly is what was
// meant, and it is what makes the call typecheck without a cast.
type CustomersListQueries = NonNullable<Parameters<typeof api.api_Customers_list>[0]>["queries"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const retrieveCustomersOptions = (queries?: CustomersListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["customers", queries, config] as const,
  queryFn: () => api.api_Customers_list({ queries, ...config }),
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
