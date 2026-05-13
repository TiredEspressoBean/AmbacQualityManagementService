import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type ProcessesListQueries = NonNullable<operations["api_Processes_list"]["parameters"]["query"]>;
type ProcessesListResponse = components["schemas"]["PaginatedProcessesList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const processesOptions = (queries?: ProcessesListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["process", queries, config] as const,
    queryFn: () =>
      api.api_Processes_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<ProcessesListResponse>,
  });

export const processesMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "Processes", "Processes"] as const,
    queryFn: () => api.api_Processes_metadata_retrieve(),
  });

export function useRetrieveProcesses(
  queries?: ProcessesListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof processesOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...processesOptions(queries, config),
    ...options,
  });
}
