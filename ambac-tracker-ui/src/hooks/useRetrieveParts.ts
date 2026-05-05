import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type PartsListQueries = NonNullable<operations["api_Parts_list"]["parameters"]["query"]>;
type PartsListResponse = components["schemas"]["PaginatedPartsList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveParts(
  queries?: PartsListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<PartsListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<PartsListResponse, Error>({
    queryKey: ["part", queries, config],
    queryFn: () =>
      api.api_Parts_list(
        // Cast: zodios's deep-readonly Args type derived from the runtime zod
        // schema is permissive in places the openapi-typescript queries shape
        // is strict (e.g. nullable string fields). We've already constrained
        // the public `queries` signature with the strict type above; the
        // call-site cast is a contained widening just for the runtime client.
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<PartsListResponse>,
    ...options,
  });
}