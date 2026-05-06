import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type StepsListQueries = NonNullable<operations["api_Steps_list"]["parameters"]["query"]>;
type StepsListResponse = components["schemas"]["PaginatedStepsList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveSteps(
  queries?: StepsListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<StepsListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<StepsListResponse, Error>({
    queryKey: ["step", queries, config],
    queryFn: () =>
      api.api_Steps_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<StepsListResponse>,
    ...options,
  });
}
