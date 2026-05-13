import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type StepsListQueries = NonNullable<operations["api_Steps_list"]["parameters"]["query"]>;
type StepsListResponse = components["schemas"]["PaginatedStepsList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const stepsOptions = (queries?: StepsListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["step", queries, config] as const,
    queryFn: () =>
      api.api_Steps_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<StepsListResponse>,
  });

export const stepsMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "Steps", "Steps"] as const,
    queryFn: () => api.api_Steps_metadata_retrieve(),
  });

export function useRetrieveSteps(
  queries?: StepsListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof stepsOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...stepsOptions(queries, config),
    ...options,
  });
}
